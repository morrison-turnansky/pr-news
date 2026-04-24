"""Output formatting and export for PR reviews."""

import json

from pr_filter.data_structs import ReviewResult, Verdict


def format_review(result: ReviewResult, show_all_comments: bool = True) -> str:
    """
    Format a ReviewResult as human-readable text.

    Args:
        result: The review result to format
        show_all_comments: If True, show all comments. If False, only show critical/major.

    Returns:
        Formatted review string
    """
    lines = []

    # Header separator
    lines.append("  " + "─" * 70)

    # Filter comments based on show_all_comments
    if show_all_comments:
        comments_to_show = result.comments
    else:
        comments_to_show = [c for c in result.comments if c.severity in ["critical", "major"]]

    # Review comments section
    if comments_to_show:
        lines.append("  REVIEW COMMENTS:")
        lines.append("  " + "─" * 70)

        for i, comment in enumerate(comments_to_show, 1):
            # Comment header with severity badge
            severity_badge = f"[{comment.severity}]".ljust(12)
            location = f"{comment.file}:{comment.line}" if comment.line > 0 else comment.file
            lines.append(f"  {i}. {severity_badge} {location}")

            # Category
            if comment.category:
                lines.append(f"     Category: {comment.category}")

            # Message (word-wrapped to 66 chars, indented)
            message_lines = _wrap_text(comment.message, 66)
            lines.append(f"     Message: {message_lines[0]}")
            for msg_line in message_lines[1:]:
                lines.append(f"              {msg_line}")

            # Suggestion (if present)
            if comment.suggestion:
                suggestion_lines = _wrap_text(comment.suggestion, 66)
                lines.append(f"     Suggestion: {suggestion_lines[0]}")
                for sug_line in suggestion_lines[1:]:
                    lines.append(f"                 {sug_line}")

            # Verdict
            verdict_text = "BLOCK" if comment.verdict == Verdict.BLOCK else "PASS"
            lines.append(f"     Verdict: {verdict_text}")
            lines.append("")  # Blank line between comments
    else:
        lines.append("  REVIEW COMMENTS: None")
        lines.append("")

    # Summary section
    lines.append("  SUMMARY:")
    lines.append("  " + "─" * 70)
    lines.append(
        f"  Total Issues: {result.summary.total_issues} "
        f"(Critical: {result.summary.critical}, "
        f"Major: {result.summary.major}, "
        f"Minor: {result.summary.minor}, "
        f"Suggestions: {result.summary.suggestions})"
    )

    # Overall verdict
    verdict_emoji = "🚫" if result.verdict == Verdict.BLOCK else "✓"
    verdict_text = "BLOCK" if result.verdict == Verdict.BLOCK else "PASS"
    lines.append(f"  Overall Verdict: {verdict_emoji} {verdict_text}")
    lines.append("")

    # Explanation (word-wrapped)
    if result.summary.explanation:
        lines.append("  Explanation:")
        explanation_lines = _wrap_text(result.summary.explanation, 68)
        for exp_line in explanation_lines:
            lines.append(f"  {exp_line}")
        lines.append("")

    # Footer separator
    lines.append("  " + "─" * 70)

    return "\n".join(lines)


def _wrap_text(text: str, width: int) -> list[str]:
    """
    Wrap text to specified width, preserving words.

    Args:
        text: Text to wrap
        width: Maximum line width

    Returns:
        List of wrapped lines
    """
    if not text:
        return [""]

    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        word_length = len(word)

        # If adding this word would exceed width, start new line
        if current_length + word_length + len(current_line) > width and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = word_length
        else:
            current_line.append(word)
            current_length += word_length

    # Add final line
    if current_line:
        lines.append(" ".join(current_line))

    return lines if lines else [""]


def print_review(result: ReviewResult, show_all_comments: bool = True) -> None:
    """
    Print a formatted review to stdout.

    Args:
        result: The review result to print
        show_all_comments: If True, show all comments. If False, only show critical/major.
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
