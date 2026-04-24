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

    with GitHubClient(token=github_token, repo=filter_criteria.repo) as client:
        pr_reviews = client.get_prs_by_filter(
            authors=filter_criteria.authors,
            labels=filter_criteria.labels,
            created_after=filter_criteria.created_after,
            created_before=filter_criteria.created_before,
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
                diff = client.get_pr_diff(pr.number)
            except Exception as e:
                print(f"  WARNING: Failed to fetch diff for PR #{pr.number}: {e}")
                diff = ""

            pull_request = PullRequest(
                pr_number=pr.number,
                title=pr.title,
                url=pr.url,
                files_changed=[],  # Could parse from diff if needed
                diff=diff,
                created_at=created,
                updated_at=created,
                author=pr.author,
            )
            all_prs.append(pull_request)

    print(f"\n✅ Fetched {len(all_prs)} PRs")
    return all_prs
