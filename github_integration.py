import os
import re
import sys
from pathlib import Path
import json

from exceptions import NetworkManagerError
from logger_setup import get_project_or_exe_root

def check_github_cli_auth() -> tuple[bool, str]:
    """
    Checks if GitHub CLI is installed and the user is authenticated.

    Returns:
        A tuple (is_ok, message).
        is_ok is True if everything is fine, False otherwise.
        message contains the status or error.
    """
    try:
        # Need to import here to avoid circular dependency with logger_setup
        from logic.command_utils import run_system_command
        run_system_command(["gh", "auth", "status"], "GitHub CLI authentication check failed.")
        return (True, "GitHub CLI is ready.")
    except NetworkManagerError as e:
        # Distinguish between 'gh not found' and 'not logged in'.
        if "not found" in str(e):
            return (False, "GitHub CLI ('gh') is not installed. Please install it from https://cli.github.com/")
        else:
            return (False, "You are not logged in to GitHub CLI. Please run 'gh auth login' in your terminal.")

def _get_repo_from_packaged_info() -> str | None:
    """
    Tries to read the repository name from a 'git_info.json' file,
    which is expected to exist alongside the executable when packaged.
    """
    if getattr(sys, 'frozen', False): # Checks if running as a bundled exe
        try:
            info_file = get_project_or_exe_root() / "git_info.json"
            if info_file.is_file():
                data = json.loads(info_file.read_text(encoding='utf-8'))
                return data.get("repository")
        except (IOError, json.JSONDecodeError):
            return None
    return None

def get_repo_from_git_config() -> str | None:
    """
    Reads the 'origin' remote URL from the local Git config and extracts the
    'owner/repo' string.

    This function now first checks for a packaged `git_info.json` file.

    Returns:
        The 'owner/repo' string (e.g., "atkeppu/NetPilot") or None if not found.
    """
    # First, try the method for the packaged application
    packaged_repo = _get_repo_from_packaged_info()
    if packaged_repo:
        return packaged_repo

    # Determine the project root directory based on this file's location.
    # This ensures the git command runs in the correct directory.
    project_root = get_project_or_exe_root()

    try:
        # Need to import here to avoid circular dependency with logger_setup
        from logic.command_utils import run_system_command
        result = run_system_command(
            ["git", "remote", "get-url", "origin"],
            "Could not get remote URL for 'origin'.",
            cwd=str(project_root)  # Execute the command in the project's root directory
        )
        url = result.stdout.decode('utf-8').strip()

        # Regex to match both HTTPS and SSH URLs
        # e.g., https://github.com/owner/repo.git or git@github.com:owner/repo.git
        match = re.search(r'github\.com[/:]([\w-]+/[\w.-]+?)(\.git)?$', url)
        if match:
            # Group 1 captures the 'owner/repo' part without the optional .git suffix
            return match.group(1).removesuffix('.git')
        return None
    except NetworkManagerError as e:
        # Provide more context on failure. This helps diagnose if git isn't installed,
        # not in a repo, or if the 'origin' remote doesn't exist.
        print(f"DEBUG: Failed to get git remote URL. Reason: {e}", file=sys.stderr)
        # The function's contract is to return None on failure, so we don't re-raise.
        return None


def create_github_release(tag: str, title: str, notes: str, repo: str | None = None, asset_paths: list[str] | None = None) -> str | None:
    """
    Creates a new release on GitHub and optionally uploads an asset.

    Args:
        tag: The version tag for the release (e.g., "v1.2.0").
        title: The title of the release.
        notes: The release notes.
        repo: Optional. The GitHub repository in "owner/repo" format. If not provided,
              it will be detected from the local Git configuration.
        asset_paths: Optional list of local paths to files to be uploaded as release assets.

    Returns:
        The URL of the new release, or None if an error occurs.
    """
    try:
        # Need to import here to avoid circular dependency with logger_setup
        from logic.command_utils import run_system_command
        # Build the command as a list of arguments. shell=False handles quoting safely.
        if not repo:
            repo = get_repo_from_git_config()
            if not repo:
                raise NetworkManagerError("Could not determine GitHub repository. Please ensure you are in a Git repository with a configured 'origin' remote.")
        command = [
            'gh', 'release', 'create', tag,
            '--repo', repo,
            '--title', title,
        ]
        if notes:
            command.extend(['--notes', notes])
        else:
            command.append('--generate-notes')

        if asset_paths:
            command.extend(asset_paths)

        # Use a much longer timeout for release creation, as asset uploads can be slow.
        result = run_system_command(
            command,
            f"Failed to create GitHub release for tag {tag}",
            timeout=300  # 5 minutes
        )
        return result.stdout.decode('utf-8').strip()
    except NetworkManagerError as e:
        error_output = str(e).lower()

        # Provide more specific, user-friendly error messages for common failures.
        if "release with tag" in error_output and "already exists" in error_output:
            raise NetworkManagerError(
                f"A release for tag '{tag}' already exists on GitHub. Please update the version number.",
                code='TAG_EXISTS'
            ) from e
        if "bad credentials" in error_output or "authentication required" in error_output:
            raise NetworkManagerError(
                "Authentication with GitHub failed. Your token may have expired. Please run 'gh auth login' in your terminal to re-authenticate.",
                code='AUTH_FAILED'
            ) from e
        if "could not resolve to a repository" in error_output or "not found" in error_output:
            raise NetworkManagerError(
                f"The repository '{repo}' could not be found. Please check for typos or ensure you have access to it.",
                code='REPO_NOT_FOUND'
            ) from e

        # For any other errors, raise a generic but informative exception.
        # The original error details from 'gh' are included.
        raise NetworkManagerError(f"Failed to create GitHub release for tag {tag}:\n\n{str(e)}") from e