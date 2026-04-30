"""Data models for PR review filter."""

import os
from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel, Field


class Verdict(IntEnum):
    """Verdict for PR critique.

    CRITICAL: This MUST remain an IntEnum with integer values.
    - BLOCK = 0 (integer)
    - PASS = 1 (integer)

    DO NOT change to string enum or add string validators.
    The prompt instructs Claude to output integers (0, 1), and the schema
    expects {"type": "integer", "enum": [0, 1]}. Any mismatch causes
    error_max_structured_output_retries.

    If you modify this, update prompts.py to match and run:
    python3 -m pytest tests/test_schema_prompt_alignment.py -v
    """

    BLOCK = 0
    PASS = 1


class Confidence(IntEnum):
    """Confidence level for critique verdict."""

    HIGH = 0
    MEDIUM = 1


class PRFilter(BaseModel):
    """
    Flexible PR filtering criteria.

    All fields are optional. None/empty values match all PRs.
    """

    authors: list[str] | None = None
    labels: list[str] | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    repo: str = ""
    is_merged: bool | None = None
    is_open: bool | None = None
    is_draft: bool | None = None


class PullRequest(BaseModel):
    """GitHub PR metadata and content."""

    pr_number: int
    title: str
    url: str
    files_changed: list[str]
    diff: str
    created_at: datetime
    updated_at: datetime
    author: str

    @property
    def diff_lines(self) -> int:
        """Count of changed lines in diff (additions + deletions)."""
        if not self.diff:
            return 0
        lines = self.diff.splitlines()
        additions = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
        return additions + deletions


class ReviewComment(BaseModel):
    """Structured review comment for a specific file/line."""

    file: str = Field(..., description="Relative file path from repository root")
    line: int = Field(..., description="Line number in the file")
    severity: str = Field(
        ..., description="Issue severity level: critical, major, minor, or suggestion"
    )
    category: str = Field(
        ..., description="Issue category: correctness, performance, security, or style"
    )
    message: str = Field(..., description="Detailed description of the issue")
    suggestion: str = Field(default="", description="Optional fix suggestion")
    verdict: Verdict = Field(default=Verdict.PASS, description="Verdict for this comment")


class ReviewSummary(BaseModel):
    """Summary statistics for a PR review."""

    total_issues: int = Field(default=0, description="Total number of issues found")
    critical: int = Field(default=0, description="Number of critical issues")
    major: int = Field(default=0, description="Number of major issues")
    minor: int = Field(default=0, description="Number of minor issues")
    suggestions: int = Field(default=0, description="Number of suggestions")
    verdict: Verdict = Field(default=Verdict.PASS, description="Overall verdict")
    explanation: str = Field(default="", description="Overall assessment of the PR")


class ReviewResult(BaseModel):
    """Structured review result from Claude Code agent (simplified)."""

    pr_number: int
    title: str
    url: str
    author: str
    created_at: datetime
    updated_at: datetime
    files_changed: list[str]
    comments: str
    summary: str
    verdict: int

    @property
    def has_critical_issue(self) -> bool:
        """True if verdict is BLOCK."""
        return self.verdict == 0  # 0 = BLOCK


class ModelParams(BaseModel):
    """Claude model parameters."""

    model: str = "claude-sonnet-4-5@20250929"
    max_tokens: int = 2000


class PRReviewConfig(BaseModel):
    """Main configuration for PR review pipeline (Claude Code agent)."""

    repository: str
    workspace_path: str
    skill_paths: list[str] = Field(default_factory=list)
    filter_config: PRFilter = Field(default_factory=PRFilter)
    vertex_project_id: str | None = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_VERTEX_PROJECT_ID")
    )
    cloud_ml_region: str | None = Field(default_factory=lambda: os.getenv("CLOUD_ML_REGION"))
    use_vertex: bool = Field(default_factory=lambda: os.getenv("CLAUDE_CODE_USE_VERTEX") == "1")
    google_credentials_path: str | None = Field(
        default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )

    def verify_vertex_env(self) -> None:
        """Verify Vertex AI configuration.

        Raises:
            ValueError: If required field missing when use_vertex is True
        """
        if not self.use_vertex:
            return

        required_fields = {
            "vertex_project_id": "Vertex AI project ID",
            "cloud_ml_region": "Cloud ML region",
            "google_credentials_path": "Google credentials path",
        }

        for field, description in required_fields.items():
            if not getattr(self, field):
                raise ValueError(f"{field} required for Vertex AI ({description})")

    def get_vertex_env(self) -> dict[str, str]:
        """Get Vertex AI environment variables for subprocess.

        Returns:
            Environment variable dict for Claude Code CLI
        """
        env = {}
        if self.vertex_project_id:
            env["ANTHROPIC_VERTEX_PROJECT_ID"] = self.vertex_project_id
        if self.cloud_ml_region:
            env["CLOUD_ML_REGION"] = self.cloud_ml_region
        if self.use_vertex:
            env["CLAUDE_CODE_USE_VERTEX"] = "1"
        if self.google_credentials_path:
            env["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_credentials_path
        return env


class ReviewOutputSchema(BaseModel):
    """Schema for complete Claude Code review output (simplified for reliability)."""

    comments: str = Field(default="", description="Review comments as text block")
    summary: str = Field(default="", description="Summary of the review as text")
    verdict: int = Field(default=1, description="Overall verdict: 0 for BLOCK, 1 for PASS")
