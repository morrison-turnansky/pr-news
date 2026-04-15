"""Diff reduction functionality to filter PRs to relevant Dynamo/Inductor changes."""

import re
from pr_filter.models import PullRequest
from pr_filter.config import PRReviewConfig


def reduce_diff(pr: PullRequest, config: PRReviewConfig) -> str:
    """
    Reduce PR diff to relevant directories and cap size.

    Args:
        pr: PullRequest with full diff
        config: Configuration with diff_reduction settings

    Returns:
        Reduced diff string (may be empty if no relevant changes)
    """
    priority_dirs = config.diff_reduction.priority_dirs
    max_lines = config.diff_reduction.max_lines

    # Split diff into individual file chunks
    file_chunks = _split_diff_by_file(pr.diff)

    # Filter to priority directories
    relevant_chunks = []
    for file_path, chunk in file_chunks:
        if _is_relevant_file(file_path, priority_dirs):
            relevant_chunks.append(chunk)

    # If no relevant chunks, return empty string
    if not relevant_chunks:
        return ""

    # Combine relevant chunks
    combined_diff = "\n\n".join(relevant_chunks)

    # Cap at max_lines if needed
    if len(combined_diff.splitlines()) > max_lines:
        combined_diff = _cap_diff_lines(combined_diff, max_lines)

    return combined_diff


def _split_diff_by_file(diff: str) -> list[tuple[str, str]]:
    """
    Split unified diff into chunks per file.

    Returns:
        List of (file_path, chunk_text) tuples
    """
    if not diff:
        return []

    chunks = []
    current_file = None
    current_chunk = []

    for line in diff.splitlines():
        # Detect file header (diff --git a/... b/...)
        if line.startswith("diff --git "):
            # Save previous chunk if exists
            if current_file and current_chunk:
                chunks.append((current_file, "\n".join(current_chunk)))

            # Extract file path from "diff --git a/path b/path"
            match = re.search(r'b/([\w/_.-]+)', line)
            if match:
                current_file = match.group(1)
                current_chunk = [line]
            else:
                current_file = None
                current_chunk = []
        else:
            # Accumulate lines for current file
            if current_file is not None:
                current_chunk.append(line)

    # Save final chunk
    if current_file and current_chunk:
        chunks.append((current_file, "\n".join(current_chunk)))

    return chunks


def _is_relevant_file(file_path: str, priority_dirs: list[str]) -> bool:
    """
    Check if file is in a priority directory.

    Excludes:
    - test/ directories
    - doc/ or docs/ directories
    - Files not in priority_dirs
    """
    # Exclude test files
    if file_path.startswith("test/") or "/test/" in file_path:
        return False

    # Exclude docs
    if file_path.startswith("docs/") or file_path.startswith("doc/"):
        return False

    # Check if file is in any priority directory
    for priority_dir in priority_dirs:
        if file_path.startswith(priority_dir):
            return True

    return False


def _cap_diff_lines(diff: str, max_lines: int) -> str:
    """
    Cap diff to max_lines while preserving structure.

    Prioritizes:
    1. Core module files (symbolic_convert.py, scheduler.py, codegen/)
    2. Functions with deletions or modifications
    3. Concurrency/memory/numerical code

    For simplicity in v0.1.0, we just take the first max_lines.
    Future: implement smart prioritization.
    """
    lines = diff.splitlines()

    if len(lines) <= max_lines:
        return diff

    # Simple approach: take first max_lines
    # Preserve diff structure by including file headers
    capped_lines = lines[:max_lines]

    # Add a marker indicating truncation
    capped_lines.append("... (diff truncated)")

    return "\n".join(capped_lines)
