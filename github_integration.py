import subprocess
import os
import re
from exceptions import NetworkManagerError

def check_github_cli_auth() -> tuple[bool, str]:
    """
    Checks if GitHub CLI is installed and the user is authenticated.

    Returns:
        A tuple (is_ok, message).
        is_ok is True if everything is fine, False otherwise.
        message contains the status or error.
    """
    # This flag prevents a console window from flashing on Windows.
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        subprocess.run(["gh", "auth", "status"], check=True, capture_output=True, shell=False, startupinfo=startupinfo)
        return (True, "GitHub CLI is ready.")
    except FileNotFoundError:
        return (False, "GitHub CLI ('gh') is not installed. Please install it from https://cli.github.com/")
    except subprocess.CalledProcessError:
        return (False, "You are not logged in to GitHub CLI. Please run 'gh auth login' in your terminal.")

def get_repo_from_git_config() -> str | None:
    """
    Reads the 'origin' remote URL from the local Git config and extracts the
    'owner/repo' string.

    Returns:
        The 'owner/repo' string (e.g., "atkeppu/NetPilot") or None if not found.
    """
    try:
        # This flag prevents a console window from flashing on Windows.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=True, capture_output=True, text=True, encoding='utf-8', startupinfo=startupinfo
        )
        url = result.stdout.strip()

        # Regex to match both HTTPS and SSH URLs
        # e.g., https://github.com/owner/repo.git or git@github.com:owner/repo.git
        match = re.search(r'github\.com[/:]([\w-]+/[\w.-]+?)(\.git)?$', url)
        if match:
            repo_name = match.group(1)
            # Remove .git suffix if it exists
            if repo_name.endswith('.git'):
                return repo_name[:-4]
            return repo_name
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def create_github_release(tag: str, title: str, notes: str, repo: str | None = None, asset_path: str | None = None) -> str:
    """
    Creates a new release on GitHub and optionally uploads an asset.

    Args:
        tag: The version tag for the release (e.g., "v1.2.0").
        title: The title of the release.
        notes: The release notes.
        repo: Optional. The GitHub repository in "owner/repo" format. If not provided,
              it will be detected from the local Git configuration.
        asset_path: Optional local path to the file to be uploaded as a release asset.

    Returns:
        The URL of the new release.
    """
    try:
        # Build the command as a list of arguments. shell=False handles quoting safely.
        if not repo:
            repo = get_repo_from_git_config()
            if not repo:
                raise NetworkManagerError("Could not determine GitHub repository. Please ensure you are in a Git repository with a configured 'origin' remote.")
        command = [
            'gh', 'release', 'create', tag,
            '--repo', repo,
            '--title', title,
            '--notes', notes
        ]
        if asset_path:
            command.append(asset_path)

        # This flag prevents a console window from flashing on Windows.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(command, shell=False, check=True, capture_output=True, text=True, encoding='utf-8', startupinfo=startupinfo)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or e.stdout.strip()

        # Provide a more specific error message if the tag already exists.
        if "release with tag" in error_output and "already exists" in error_output:
            raise NetworkManagerError(f"A release for tag '{tag}' already exists on GitHub. Please update the version number.") from e

        raise NetworkManagerError(f"Failed to create GitHub release for tag {tag}:\n\n{error_output}") from e

publish_to_github = create_github_release # Alias for backward compatibility if needed