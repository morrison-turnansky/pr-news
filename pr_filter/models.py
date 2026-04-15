"""Data models for PR review filter."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class PullRequest:
    """GitHub PR metadata and content."""
    pr_number: int
    title: str
    url: str
    files_changed: list[str]
    diff: str  # Full diff text
    created_at: datetime
    updated_at: datetime
    author: str

    @property
    def diff_lines(self) -> int:
        """Count of lines in diff."""
        return len(self.diff.splitlines())


@dataclass
class CritiquedPR:
    """PR with AI critique verdict."""
    # Inherited from PullRequest
    pr_number: int
    title: str
    url: str
    files_changed: list[str]
    diff: str
    created_at: datetime
    updated_at: datetime
    author: str

    # Critique results
    verdict: Literal["BLOCK", "PASS"]
    confidence: Literal["HIGH", "MEDIUM"] | None = None
    issue_explanation: str = ""  # Populated if verdict == BLOCK
    reduced_diff_lines: int = 0  # Line count after diff reduction

    @property
    def has_critical_issue(self) -> bool:
        """True if verdict is BLOCK."""
        return self.verdict == "BLOCK"


@dataclass
class SummaryStats:
    """Summary statistics for PR analysis."""
    blocked_count: int
    passed_count: int

    @property
    def total_analyzed(self) -> int:
        return self.blocked_count + self.passed_count

    @property
    def block_rate(self) -> float:
        """Percentage of PRs blocked."""
        if self.total_analyzed == 0:
            return 0.0
        return (self.blocked_count / self.total_analyzed) * 100


@dataclass
class FrontPage:
    """Front page of critical PRs (BLOCK verdicts only)."""
    generated_at: datetime
    blocked_prs: list[CritiquedPR]  # Only verdict == BLOCK
    summary_stats: SummaryStats

    def __post_init__(self):
        """Validate all PRs have BLOCK verdict."""
        for pr in self.blocked_prs:
            if pr.verdict != "BLOCK":
                raise ValueError(
                    f"PR {pr.pr_number} has verdict {pr.verdict}, "
                    "but FrontPage should only contain BLOCK verdicts"
                )

    def sort_by_confidence(self) -> None:
        """Sort blocked PRs: HIGH confidence first, then MEDIUM, then None."""
        confidence_order = {"HIGH": 0, "MEDIUM": 1, None: 2}
        self.blocked_prs.sort(
            key=lambda pr: confidence_order.get(pr.confidence, 2)
        )
