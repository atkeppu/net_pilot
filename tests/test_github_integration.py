import unittest
from unittest.mock import patch, Mock
import subprocess

from github_integration import check_github_cli_auth, publish_to_github, get_repo_from_git_config, create_github_release
from exceptions import NetworkManagerError

class TestGitHubIntegration(unittest.TestCase):
    """
    Unit tests for the github_integration module.
    """

    @patch('github_integration.subprocess.run')
    def test_check_auth_success(self, mock_run):
        """Test check_github_cli_auth when gh is installed and user is logged in."""
        # Arrange
        mock_run.return_value = Mock(returncode=0)

        # Act
        is_ok, message = check_github_cli_auth()

        # Assert
        self.assertTrue(is_ok)
        self.assertEqual(message, "GitHub CLI is ready.")
        mock_run.assert_called_once()
        self.assertIn("gh", mock_run.call_args[0][0])
        self.assertIn("auth", mock_run.call_args[0][0])
        self.assertIn("status", mock_run.call_args[0][0])

    @patch('github_integration.subprocess.run')
    def test_check_auth_gh_not_found(self, mock_run):
        """Test check_github_cli_auth when gh command is not found."""
        # Arrange
        mock_run.side_effect = FileNotFoundError

        # Act
        is_ok, message = check_github_cli_auth()

        # Assert
        self.assertFalse(is_ok)
        self.assertIn("not installed", message)

    @patch('github_integration.subprocess.run')
    def test_check_auth_not_logged_in(self, mock_run):
        """Test check_github_cli_auth when user is not logged in."""
        # Arrange
        mock_run.side_effect = subprocess.CalledProcessError(1, "gh auth status")

        # Act
        is_ok, message = check_github_cli_auth()

        # Assert
        self.assertFalse(is_ok)
        self.assertIn("not logged in", message)

    @patch('github_integration.subprocess.run')
    def test_publish_success_no_asset(self, mock_run):
        """Test successful publishing of a release without an asset."""
        # Arrange
        expected_url = "https://github.com/user/repo/releases/tag/v1.0.0"
        mock_run.return_value = Mock(stdout=expected_url)

        # Act
        result_url = publish_to_github("v1.0.0", "user/repo", "Title", "Notes")

        # Assert
        self.assertEqual(result_url, expected_url)
        self.assertNotIn("asset.exe", " ".join(mock_run.call_args[0][0]))

    @patch('github_integration.subprocess.run')
    def test_publish_success_with_asset(self, mock_run):
        """Test successful publishing of a release with an asset."""
        # Arrange
        mock_run.return_value = Mock(stdout="some_url")
        asset_path = "dist/app.exe"

        # Act
        publish_to_github("v1.0.0", "user/repo", "Title", "Notes", asset_path=asset_path)

        # Assert
        self.assertIn(asset_path, mock_run.call_args[0][0])

    @patch('github_integration.subprocess.run')
    def test_publish_fails_if_tag_exists(self, mock_run):
        """Test that a specific error is raised if the release tag already exists."""
        # Arrange
        error_output = "HTTP 422: A release with tag 'v1.0.0' already exists."
        mock_run.side_effect = subprocess.CalledProcessError(1, "gh release create", stderr=error_output)

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            publish_to_github("v1.0.0", "user/repo", "Title", "Notes")
        
        self.assertIn("already exists on GitHub", str(cm.exception))

    @patch('github_integration.subprocess.run')
    def test_publish_fails_with_generic_error(self, mock_run):
        """Test that a generic error is wrapped correctly."""
        # Arrange
        error_output = "Some other generic error."
        mock_run.side_effect = subprocess.CalledProcessError(1, "gh release create", stderr=error_output)

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            publish_to_github("v1.0.0", "user/repo", "Title", "Notes")
        
        self.assertIn(error_output, str(cm.exception))

    @patch('github_integration.get_repo_from_git_config', return_value='owner/detected')
    @patch('github_integration.subprocess.run')
    def test_create_release_uses_detected_repo(self, mock_run, mock_get_repo):
        """Test that create_github_release calls get_repo_from_git_config if repo is not provided."""
        # Act
        create_github_release("v1.0", "Title", "Notes")

        # Assert
        mock_get_repo.assert_called_once()
        # Check that the detected repo name was used in the command
        command_str = " ".join(mock_run.call_args[0][0])
        self.assertIn("--repo owner/detected", command_str)

class TestGetRepoFromGitConfig(unittest.TestCase):
    """Tests for the get_repo_from_git_config function."""

    @patch('github_integration.subprocess.run')
    def test_get_repo_from_https_url(self, mock_run):
        """Test parsing a standard HTTPS remote URL."""
        mock_run.return_value.stdout = "https://github.com/test-owner/test-repo.git"
        self.assertEqual(get_repo_from_git_config(), "test-owner/test-repo")

    @patch('github_integration.subprocess.run')
    def test_get_repo_from_ssh_url(self, mock_run):
        """Test parsing a standard SSH remote URL."""
        mock_run.return_value.stdout = "git@github.com:test-owner/test-repo.git"
        self.assertEqual(get_repo_from_git_config(), "test-owner/test-repo")

    @patch('github_integration.subprocess.run')
    def test_get_repo_from_url_without_git_suffix(self, mock_run):
        """Test parsing a URL without the .git suffix."""
        mock_run.return_value.stdout = "https://github.com/test-owner/test-repo"
        self.assertEqual(get_repo_from_git_config(), "test-owner/test-repo")

    @patch('github_integration.subprocess.run')
    def test_get_repo_command_fails(self, mock_run):
        """Test that None is returned if the git command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git remote get-url origin")
        self.assertIsNone(get_repo_from_git_config())

    @patch('github_integration.subprocess.run')
    def test_get_repo_not_a_git_repo(self, mock_run):
        """Test that None is returned if not in a git repository."""
        mock_run.side_effect = FileNotFoundError
        self.assertIsNone(get_repo_from_git_config())

if __name__ == '__main__':
    unittest.main()