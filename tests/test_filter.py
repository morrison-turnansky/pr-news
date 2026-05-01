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


@pytest.fixture
def sample_prs():
    """Create sample PRs with different diff characteristics."""
    return [
        PullRequest(
            pr_number=1,
            title="Small PR",
            url="https://github.com/test/repo/pull/1",
            author="user1",
            files_changed=["src/module.py"],
            diff="+line1\n+line2\n-line3",  # 3 lines
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        PullRequest(
            pr_number=2,
            title="Large PR",
            url="https://github.com/test/repo/pull/2",
            author="user2",
            files_changed=["src/a.py", "src/b.py", "src/c.py"],
            diff="\n".join([f"+line{i}" for i in range(100)]),  # 100 lines
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        PullRequest(
            pr_number=3,
            title="Test-only PR",
            url="https://github.com/test/repo/pull/3",
            author="user3",
            files_changed=["tests/test_module.py", "tests/test_utils.py"],
            diff="+test line",  # 1 line
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        PullRequest(
            pr_number=4,
            title="Mixed PR",
            url="https://github.com/test/repo/pull/4",
            author="user4",
            files_changed=["src/module.py", "tests/test_module.py"],
            diff="+line1\n+line2",  # 2 lines
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]


class TestIsTestFile:
    """Test _is_test_file helper."""

    def test_recognizes_test_prefix(self):
        """Verify test file recognition for test prefix patterns."""
        from pr_filter.filter import _is_test_file

        assert _is_test_file("test_module.py") is True
        assert _is_test_file("tests/test_utils.py") is True
        assert _is_test_file("src/tests/test_file.cpp") is True

    def test_recognizes_test_infix(self):
        """Verify test file recognition for test infix patterns."""
        from pr_filter.filter import _is_test_file

        assert _is_test_file("module_test.py") is True
        assert _is_test_file("src/testing/helper.py") is True

    def test_rejects_non_test_files(self):
        """Verify non-test files are not recognized as test files."""
        from pr_filter.filter import _is_test_file

        assert _is_test_file("src/module.py") is False
        assert _is_test_file("README.md") is False


class TestDiffFilterMaxLines:
    """Test diff_filter with max_lines_changed."""

    def test_filters_out_large_prs(self, sample_prs):
        """Verify diff_filter removes PRs exceeding max_lines_changed."""
        from pr_filter.filter import diff_filter

        result = diff_filter(sample_prs, max_lines_changed=10)
        pr_numbers = [pr.pr_number for pr in result]
        assert 1 in pr_numbers  # 3 lines - keep
        assert 2 not in pr_numbers  # 100 lines - filter out
        assert 3 in pr_numbers  # 1 line - keep
        assert 4 in pr_numbers  # 2 lines - keep

    def test_none_keeps_all(self, sample_prs):
        """Verify None max_lines_changed keeps all PRs."""
        from pr_filter.filter import diff_filter

        result = diff_filter(sample_prs, max_lines_changed=None)
        assert len(result) == len(sample_prs)


class TestDiffFilterMaxFiles:
    """Test diff_filter with max_files_changed."""

    def test_filters_out_multi_file_prs(self, sample_prs):
        """Verify diff_filter removes PRs exceeding max_files_changed."""
        from pr_filter.filter import diff_filter

        result = diff_filter(sample_prs, max_files_changed=2)
        pr_numbers = [pr.pr_number for pr in result]
        assert 1 in pr_numbers  # 1 file - keep
        assert 2 not in pr_numbers  # 3 files - filter out
        assert 3 in pr_numbers  # 2 files - keep
        assert 4 in pr_numbers  # 2 files - keep

    def test_none_keeps_all(self, sample_prs):
        """Verify None max_files_changed keeps all PRs."""
        from pr_filter.filter import diff_filter

        result = diff_filter(sample_prs, max_files_changed=None)
        assert len(result) == len(sample_prs)


class TestDiffFilterOnlyTestFiles:
    """Test diff_filter with only_test_files."""

    def test_true_keeps_only_test_prs(self, sample_prs):
        """Verify only_test_files=True keeps only PRs with all test files."""
        from pr_filter.filter import diff_filter

        result = diff_filter(sample_prs, only_test_files=True)
        pr_numbers = [pr.pr_number for pr in result]
        assert 1 not in pr_numbers  # src file - filter out
        assert 2 not in pr_numbers  # src files - filter out
        assert 3 in pr_numbers  # all test files - keep
        assert 4 not in pr_numbers  # mixed - filter out

    def test_false_keeps_only_non_test_prs(self, sample_prs):
        """Verify only_test_files=False keeps only PRs with non-test files."""
        from pr_filter.filter import diff_filter

        result = diff_filter(sample_prs, only_test_files=False)
        pr_numbers = [pr.pr_number for pr in result]
        assert 1 in pr_numbers  # has non-test - keep
        assert 2 in pr_numbers  # has non-test - keep
        assert 3 not in pr_numbers  # all test - filter out
        assert 4 in pr_numbers  # has non-test - keep

    def test_none_keeps_all(self, sample_prs):
        """Verify None only_test_files keeps all PRs."""
        from pr_filter.filter import diff_filter

        result = diff_filter(sample_prs, only_test_files=None)
        assert len(result) == len(sample_prs)


class TestDiffFilterCombined:
    """Test diff_filter with multiple criteria."""

    def test_combines_all_filters(self, sample_prs):
        """Verify diff_filter applies all filter criteria together."""
        from pr_filter.filter import diff_filter

        result = diff_filter(
            sample_prs, max_lines_changed=50, max_files_changed=2, only_test_files=False
        )
        pr_numbers = [pr.pr_number for pr in result]
        assert 1 in pr_numbers  # 3 lines, 1 file, non-test - keep
        assert 2 not in pr_numbers  # 100 lines - filter out (exceeds max_lines)
        assert 3 not in pr_numbers  # all test files - filter out (only_test_files=False)
        assert 4 in pr_numbers  # 2 lines, 2 files, has non-test - keep

    def test_empty_filters_keeps_all(self, sample_prs):
        """Verify diff_filter with no filters keeps all PRs."""
        from pr_filter.filter import diff_filter

        result = diff_filter(sample_prs)
        assert len(result) == len(sample_prs)
