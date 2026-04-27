"""Parse and process Claude Code review output (simplified schema)."""

from pr_filter.data_structs import PullRequest, ReviewResult


def create_error_result(pr: PullRequest, error: Exception) -> ReviewResult:
    """Create ReviewResult for failed analysis.

    Args:
        pr: PullRequest that failed
        error: Exception that occurred

    Returns:
        ReviewResult with PASS verdict
    """
    return ReviewResult(
        pr_number=pr.pr_number,
        title=pr.title,
        url=pr.url,
        author=pr.author,
        created_at=pr.created_at,
        updated_at=pr.updated_at,
        files_changed=pr.files_changed,
        comments="",
        summary=f"Analysis failed: {str(error)}",
        verdict=1,  # 1 = PASS
    )
