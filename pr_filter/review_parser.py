"""Parse and process Claude Code review output."""

from pr_filter.data_structs import PullRequest, ReviewComment, ReviewResult, ReviewSummary, Verdict


def parse_review_comments(comments_data: list[dict]) -> list[ReviewComment]:
    """Parse review comments from Claude Code output.

    Args:
        comments_data: List of comment dictionaries

    Returns:
        List of ReviewComment objects
    """
    return [ReviewComment(**comment_dict) for comment_dict in comments_data]


def parse_review_summary(summary_data: dict, comments: list[ReviewComment]) -> ReviewSummary:
    """Parse review summary from Claude Code output.

    Provides safe defaults for all required fields when Claude returns incomplete JSON.

    Args:
        summary_data: Summary dictionary
        comments: Parsed comments for fallback count

    Returns:
        ReviewSummary object
    """
    summary_dict = dict(summary_data)

    # Provide defaults for all required fields
    summary_dict.setdefault("total_issues", len(comments))
    summary_dict.setdefault("critical", 0)
    summary_dict.setdefault("major", 0)
    summary_dict.setdefault("minor", 0)
    summary_dict.setdefault("suggestions", 0)
    summary_dict.setdefault("verdict", 1)  # INTEGER 1 = PASS, not string "PASS"
    summary_dict.setdefault("explanation", "")

    return ReviewSummary(**summary_dict)


def determine_overall_verdict(summary_verdict: Verdict, comments: list[ReviewComment]) -> Verdict:
    """Determine overall verdict.

    BLOCK if summary is BLOCK or any critical/major comment is BLOCK.

    Args:
        summary_verdict: Verdict from summary
        comments: Review comments

    Returns:
        Overall verdict
    """
    if summary_verdict == Verdict.BLOCK:
        return Verdict.BLOCK

    for comment in comments:
        if comment.verdict == Verdict.BLOCK and comment.severity in ["critical", "major"]:
            return Verdict.BLOCK

    return Verdict.PASS


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
        comments=[],
        summary=ReviewSummary(
            total_issues=0,
            critical=0,
            major=0,
            minor=0,
            suggestions=0,
            verdict=Verdict.PASS,
            explanation=f"Analysis failed: {str(error)}",
        ),
        verdict=Verdict.PASS,
    )
