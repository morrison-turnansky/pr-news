"""Filter GitHub PRs for review."""

from datetime import datetime, timedelta

import yaml
from pytorch_jira_bot.sync.github import GitHubClient

from pr_filter.data_structs import PRFilter, PullRequest


def load_users(users_file: str) -> list[str]:
    """Load GitHub usernames from YAML file."""
    with open(users_file) as f:
        users = yaml.safe_load(f)
    if not isinstance(users, list):
        raise ValueError(f"{users_file} must contain a list of usernames")
    return users


def fetch_prs(
    github_token: str,
    repo: str | None = None,
    users: list[str] | None = None,
    since_hours: int | None = None,
    filter_criteria: PRFilter | None = None,
) -> list[PullRequest]:
    """
    Fetch PRs with flexible filtering.

    Args:
        github_token: GitHub personal access token
        repo: Repository in owner/name format (deprecated, use
              filter_criteria.repo)
        users: List of GitHub usernames (deprecated, use filter_criteria.authors)
        since_hours: How far back to look (deprecated, use
                     filter_criteria.created_after)
        filter_criteria: PRFilter object with flexible filters

    Returns:
        List of PullRequest objects matching all criteria
    """
    if filter_criteria is None:
        filter_criteria = PRFilter(
            repo=repo or "pytorch/pytorch",
            authors=users,
            created_after=(datetime.now() - timedelta(hours=since_hours) if since_hours else None),
        )
    else:
        if not filter_criteria.repo:
            filter_criteria.repo = repo or "pytorch/pytorch"

    all_prs = []

    with GitHubClient(token=github_token, repos=[filter_criteria.repo]) as client:
        pr_reviews = client.get_prs_by_filter(
            authors=filter_criteria.authors,
            labels=filter_criteria.labels,
            created_after=filter_criteria.created_after,
            created_before=filter_criteria.created_before,
            is_merged=filter_criteria.is_merged,
            is_open=filter_criteria.is_open,
            is_draft=filter_criteria.is_draft,
        )

        for i, pr_review in enumerate(pr_reviews, 1):
            pr = pr_review.pr

            print(f"  Fetching diff for PR #{pr.number} ({i}/{len(pr_reviews)})...")

            created = (
                pr.updated_at
                if isinstance(pr.updated_at, datetime)
                else datetime.fromisoformat(pr.updated_at.replace("Z", "+00:00"))
            )

            try:
                diff = client.get_pr_diff(filter_criteria.repo, pr.number)
            except Exception as e:
                print(f"  WARNING: Failed to fetch diff for PR #{pr.number}: {e}")
                diff = ""

            # Parse files from diff
            files_changed = []
            for line in diff.splitlines():
                if line.startswith("diff --git"):
                    # Extract file path: "diff --git a/file.py b/file.py"
                    parts = line.split()
                    if len(parts) >= 3:
                        filepath = parts[2].removeprefix("a/")
                        files_changed.append(filepath)

            pull_request = PullRequest(
                pr_number=pr.number,
                title=pr.title,
                url=pr.url,
                files_changed=files_changed,
                diff=diff,
                created_at=created,
                updated_at=created,
                author=pr.author,
            )
            all_prs.append(pull_request)

    print(f"\n✅ Fetched {len(all_prs)} PRs")
    return all_prs


def _is_test_file(filepath: str) -> bool:
    """Check if a file path is a test file.

    Args:
        filepath: Relative file path

    Returns:
        True if path contains 'test' or 'tests'
    """
    path_lower = filepath.lower()
    return "test" in path_lower or "tests" in path_lower


def diff_filter(
    prs: list[PullRequest],
    max_lines_changed: int | None = None,
    max_files_changed: int | None = None,
    only_test_files: bool | None = None,
) -> list[PullRequest]:
    """
    Filter PRs based on diff characteristics.

    Args:
        prs: List of PRs to filter
        max_lines_changed: Maximum lines changed (filter out larger PRs)
        max_files_changed: Maximum files changed (filter out larger PRs)
        only_test_files: If True, keep only PRs where all files are test files.
                         If False, keep only PRs with at least one non-test file.
                         If None, no filtering.

    Returns:
        Filtered list of PRs
    """
    filtered = []

    for pr in prs:
        # Filter by lines changed
        if max_lines_changed is not None:
            if pr.diff_lines > max_lines_changed:
                continue

        # Filter by number of files
        if max_files_changed is not None:
            if len(pr.files_changed) > max_files_changed:
                continue

        # Filter by test files
        if only_test_files is not None:
            if not pr.files_changed:
                # No files parsed - can't determine, skip filter
                pass
            else:
                all_test = all(_is_test_file(f) for f in pr.files_changed)
                if only_test_files and not all_test:
                    continue  # Want only test files, but has non-test files
                if not only_test_files and all_test:
                    continue  # Want non-test files, but all are test files

        filtered.append(pr)

    return filtered
