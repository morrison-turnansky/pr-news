"""Tests for PR filtering functionality."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from pr_filter.data_structs import PRFilter, PullRequest
from pr_filter.filter import fetch_prs


@pytest.fixture
def mock_pr_review():
    """Create a mock PR review object."""
    mock_pr = MagicMock()
    mock_pr.number = 12345
    mock_pr.title = "Test PR"
    mock_pr.url = "https://github.com/pytorch/pytorch/pull/12345"
    mock_pr.author = "test_user"
    mock_pr.updated_at = datetime.now()

    mock_review = MagicMock()
    mock_review.pr = mock_pr

    return mock_review


@pytest.fixture
def sample_filter():
    """Create a sample PRFilter."""
    return PRFilter(
        repo="pytorch/pytorch",
        labels=["module: dynamo"],
        created_after=datetime.now() - timedelta(days=7),
    )


class TestFetchPRsWithBooleanFilters:
    """Test fetch_prs with boolean filter parameters."""

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_passes_is_merged_true(self, mock_client_class, sample_filter):
        """Verify fetch_prs passes is_merged=True to GitHub API."""
        # Setup
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []
        mock_client.get_pr_diff.return_value = "diff content"

        sample_filter.is_merged = True

        # Execute
        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        # Verify
        mock_client.get_prs_by_filter.assert_called_once()
        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["is_merged"] is True

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_passes_is_merged_false(self, mock_client_class, sample_filter):
        """Verify fetch_prs passes is_merged=False to GitHub API."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        sample_filter.is_merged = False

        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["is_merged"] is False

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_passes_is_merged_none(self, mock_client_class, sample_filter):
        """Verify fetch_prs passes is_merged=None to GitHub API."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        sample_filter.is_merged = None

        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["is_merged"] is None

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_passes_is_open_true(self, mock_client_class, sample_filter):
        """Verify fetch_prs passes is_open=True to GitHub API."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        sample_filter.is_open = True

        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["is_open"] is True

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_passes_is_open_false(self, mock_client_class, sample_filter):
        """Verify fetch_prs passes is_open=False to GitHub API."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        sample_filter.is_open = False

        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["is_open"] is False

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_passes_is_draft_true(self, mock_client_class, sample_filter):
        """Verify fetch_prs passes is_draft=True to GitHub API."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        sample_filter.is_draft = True

        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["is_draft"] is True

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_passes_is_draft_false(self, mock_client_class, sample_filter):
        """Verify fetch_prs passes is_draft=False to GitHub API."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        sample_filter.is_draft = False

        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["is_draft"] is False

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_passes_all_boolean_filters_combined(self, mock_client_class, sample_filter):
        """Verify fetch_prs passes all boolean filters together."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        sample_filter.is_merged = False
        sample_filter.is_open = True
        sample_filter.is_draft = False

        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["is_merged"] is False
        assert call_kwargs["is_open"] is True
        assert call_kwargs["is_draft"] is False

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_passes_all_filter_parameters(self, mock_client_class, sample_filter):
        """Verify fetch_prs passes all filter parameters including boolean ones."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        sample_filter.authors = ["user1", "user2"]
        sample_filter.labels = ["bug", "critical"]
        sample_filter.is_merged = False
        sample_filter.is_open = True
        sample_filter.is_draft = False

        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["authors"] == ["user1", "user2"]
        assert call_kwargs["labels"] == ["bug", "critical"]
        assert call_kwargs["created_after"] == sample_filter.created_after
        assert call_kwargs["created_before"] == sample_filter.created_before
        assert call_kwargs["is_merged"] is False
        assert call_kwargs["is_open"] is True
        assert call_kwargs["is_draft"] is False


class TestFetchPRsReturnValues:
    """Test fetch_prs return value handling."""

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_returns_pull_request_objects(self, mock_client_class, mock_pr_review):
        """Verify fetch_prs returns PullRequest objects."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = [mock_pr_review]
        mock_client.get_pr_diff.return_value = "diff content"

        filter_criteria = PRFilter(repo="pytorch/pytorch")

        result = fetch_prs(github_token="test_token", filter_criteria=filter_criteria)

        assert len(result) == 1
        assert isinstance(result[0], PullRequest)
        assert result[0].pr_number == 12345
        assert result[0].title == "Test PR"
        assert result[0].diff == "diff content"

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_returns_empty_list_when_no_prs(self, mock_client_class, sample_filter):
        """Verify fetch_prs returns empty list when no PRs match."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        result = fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        assert result == []

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_handles_diff_fetch_failure(self, mock_client_class, mock_pr_review):
        """Verify fetch_prs handles diff fetch failures gracefully."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = [mock_pr_review]
        mock_client.get_pr_diff.side_effect = Exception("Diff fetch failed")

        filter_criteria = PRFilter(repo="pytorch/pytorch")

        result = fetch_prs(github_token="test_token", filter_criteria=filter_criteria)

        assert len(result) == 1
        assert result[0].diff == ""  # Empty diff on error


class TestFetchPRsLegacyParameters:
    """Test fetch_prs backward compatibility with legacy parameters."""

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_legacy_repo_parameter(self, mock_client_class):
        """Verify fetch_prs accepts legacy repo parameter."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        # Use legacy repo parameter instead of filter_criteria
        fetch_prs(github_token="test_token", repo="pytorch/pytorch")

        # Verify it was passed to GitHubClient
        mock_client_class.assert_called_once()
        assert "pytorch/pytorch" in mock_client_class.call_args.kwargs["repos"]

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_legacy_users_parameter(self, mock_client_class):
        """Verify fetch_prs accepts legacy users parameter."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        fetch_prs(github_token="test_token", repo="pytorch/pytorch", users=["user1", "user2"])

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["authors"] == ["user1", "user2"]

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_legacy_since_hours_parameter(self, mock_client_class):
        """Verify fetch_prs accepts legacy since_hours parameter."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        before = datetime.now()
        fetch_prs(github_token="test_token", repo="pytorch/pytorch", since_hours=24)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        created_after = call_kwargs["created_after"]

        # Verify created_after is approximately 24 hours ago
        expected_time = before - timedelta(hours=24)
        assert abs((created_after - expected_time).total_seconds()) < 2


class TestFetchPRsDefaultValues:
    """Test fetch_prs default value behavior."""

    @patch("pr_filter.filter.GitHubClient")
    def test_fetch_prs_boolean_filters_default_to_none(self, mock_client_class, sample_filter):
        """Verify boolean filters default to None when not specified."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get_prs_by_filter.return_value = []

        # Don't set any boolean filters
        fetch_prs(github_token="test_token", filter_criteria=sample_filter)

        call_kwargs = mock_client.get_prs_by_filter.call_args.kwargs
        assert call_kwargs["is_merged"] is None
        assert call_kwargs["is_open"] is None
        assert call_kwargs["is_draft"] is None
