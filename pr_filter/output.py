"""Output formatting and export for PR reviews."""

import json

from pr_filter.data_structs import ReviewResult


def format_review(result: ReviewResult, show_all_comments: bool = True) -> str:
    """
    Format a ReviewResult as human-readable text.

    Args:
        result: The review result to format
        show_all_comments: Ignored (kept for compatibility)

    Returns:
        Formatted review string
    """
    lines = []

    # Header separator
    lines.append("  " + "─" * 70)

    # Review comments section
    if result.comments:
        lines.append("  REVIEW COMMENTS:")
        lines.append("  " + "─" * 70)
        # Add comments text with indentation
        for line in result.comments.splitlines():
            lines.append(f"  {line}")
    else:
        lines.append("  REVIEW COMMENTS: None")
    lines.append("")

    # Summary section
    lines.append("  SUMMARY:")
    lines.append("  " + "─" * 70)

    # Overall verdict
    verdict_emoji = "🚫" if result.verdict == 0 else "✓"
    verdict_text = "BLOCK" if result.verdict == 0 else "PASS"
    lines.append(f"  Overall Verdict: {verdict_emoji} {verdict_text}")
    lines.append("")

    # Summary text
    if result.summary:
        lines.append("  Explanation:")
        for line in result.summary.splitlines():
            lines.append(f"  {line}")
        lines.append("")

    # Footer separator
    lines.append("  " + "─" * 70)

    return "\n".join(lines)


def print_review(result: ReviewResult, show_all_comments: bool = True) -> None:
    """
    Print a formatted review to stdout.

    Args:
        result: The review result to print
        show_all_comments: Ignored (kept for compatibility)
    """
    print(format_review(result, show_all_comments))


def export_json(results: list[ReviewResult], output_path: str) -> None:
    """Export review results as JSON.

    Args:
        results: Review results to export
        output_path: Path to write JSON file
    """
    serialized_results = [r.model_dump(mode="json") for r in results]

    with open(output_path, "w") as f:
        json.dump(serialized_results, f, indent=2)
