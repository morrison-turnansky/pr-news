"""PR critique orchestration using Claude Code agent."""

from pr_filter.claude_runner import run_claude_code
from pr_filter.config import PRReviewConfig
from pr_filter.data_structs import PullRequest, ReviewResult
from pr_filter.prompts import build_review_prompt, get_review_json_schema
from pr_filter.review_parser import create_error_result


def critique_pr(pr: PullRequest, config: PRReviewConfig) -> ReviewResult:
    """Analyze PR using Claude Code agent.

    Args:
        pr: PullRequest to analyze
        config: Configuration with skill paths and Vertex AI settings

    Returns:
        ReviewResult with comments and verdict

    Raises:
        ValueError: If Vertex AI configuration missing
        FileNotFoundError: If skill files do not exist
    """
    config.verify_vertex_env()

    prompt = build_review_prompt(pr, config.skill_paths)
    schema = get_review_json_schema()

    print(f"Analyzing PR #{pr.pr_number} with Claude Code agent...")

    try:
        output = run_claude_code(prompt, config.workspace_path, schema, config, timeout=500)

        # Extract fields from simplified schema
        comments = output.get("comments", "")
        summary = output.get("summary", "")
        verdict = output.get("verdict", 1)  # Default to PASS

        return ReviewResult(
            pr_number=pr.pr_number,
            title=pr.title,
            url=pr.url,
            author=pr.author,
            created_at=pr.created_at,
            updated_at=pr.updated_at,
            files_changed=pr.files_changed,
            comments=comments,
            summary=summary,
            verdict=verdict,
        )

    except Exception as e:
        print(f"WARNING: Claude Code execution failed for PR #{pr.pr_number}: {e}")
        return create_error_result(pr, e)
