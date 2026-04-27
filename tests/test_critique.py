"""Tests for agentic PR critique functionality."""

import os
from datetime import datetime
from unittest.mock import patch

import pytest

from pr_filter.config import PRReviewConfig
from pr_filter.critique import critique_pr
from pr_filter.data_structs import PullRequest, ReviewResult


@pytest.fixture
def sample_pr():
    """Create a sample PullRequest for testing."""
    return PullRequest(
        pr_number=12345,
        title="Fix guard generation bug",
        url="https://github.com/pytorch/pytorch/pull/12345",
        files_changed=["torch/_dynamo/guards.py"],
        diff="""diff --git a/torch/_dynamo/guards.py b/torch/_dynamo/guards.py
index 123..456 100644
--- a/torch/_dynamo/guards.py
+++ b/torch/_dynamo/guards.py
@@ -42,6 +42,10 @@ def generate_guard(var):
     if isinstance(var, list):
-        return Guard(var)
+        # Skip mutation checks for performance
+        return SimpleGuard(var)
""",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user",
    )


@pytest.fixture
def config():
    """Create a test configuration."""
    return PRReviewConfig(
        repository="pytorch/pytorch",
        workspace_path="/workspace/test",
        skill_paths=[],
    )


@patch.dict(
    os.environ,
    {
        "ANTHROPIC_VERTEX_PROJECT_ID": "test-project",
        "CLOUD_ML_REGION": "us-east5",
        "CLAUDE_CODE_USE_VERTEX": "1",
        "GOOGLE_APPLICATION_CREDENTIALS": "/fake/path/creds.json",
    },
)
@patch("pr_filter.critique.run_claude_code")
def test_critique_uses_fresh_agent_per_pr(mock_run_claude, sample_pr, config):
    """
    Given: 3 PRs to analyze
    When: critique_pr() called for each
    Then: 3 separate run_claude_code() calls made, no session reuse
    """
    # Mock Claude Code to return PASS verdict
    mock_run_claude.return_value = {
        "comments": "",
        "summary": "No issues found",
        "verdict": 1,
    }

    # Create 3 PRs
    pr1 = sample_pr
    pr2 = PullRequest(
        pr_number=12346,
        title="Another PR",
        url="https://github.com/pytorch/pytorch/pull/12346",
        files_changed=["torch/_inductor/scheduler.py"],
        diff="diff --git a/torch/_inductor/scheduler.py ...",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user",
    )
    pr3 = PullRequest(
        pr_number=12347,
        title="Third PR",
        url="https://github.com/pytorch/pytorch/pull/12347",
        files_changed=["torch/_dynamo/symbolic_convert.py"],
        diff="diff --git a/torch/_dynamo/symbolic_convert.py ...",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user",
    )

    # Analyze each PR
    critique_pr(pr1, config)
    critique_pr(pr2, config)
    critique_pr(pr3, config)

    # Verify 3 separate calls were made (fresh agent pattern)
    assert mock_run_claude.call_count == 3


@patch.dict(
    os.environ,
    {
        "ANTHROPIC_VERTEX_PROJECT_ID": "test-project",
        "CLOUD_ML_REGION": "us-east5",
        "CLAUDE_CODE_USE_VERTEX": "1",
        "GOOGLE_APPLICATION_CREDENTIALS": "/fake/path/creds.json",
    },
)
@patch("pr_filter.critique.run_claude_code")
def test_critique_block_verdict_with_explanation(mock_run_claude, sample_pr, config):
    """
    Given: PR with clear bug
    When: critique_pr() called
    Then: BLOCK verdict with detailed explanation returned
    """
    mock_run_claude.return_value = {
        "comments": "Critical issue in torch/_dynamo/guards.py:42 - Guard generation logic fails to account for list mutation. "
        "Add mutation tracking in VariableTracker.",
        "summary": "Guard generation logic in guards.py line 42 fails to account for list mutation. "
        "This causes silent wrong results when the cached graph is reused with different list contents.",
        "verdict": 0,
    }

    result = critique_pr(sample_pr, config)

    assert isinstance(result, ReviewResult)
    assert result.verdict == 0  # 0 = BLOCK
    assert "list mutation" in result.summary
    assert result.pr_number == 12345
    assert "guards.py" in result.comments


@patch.dict(
    os.environ,
    {
        "ANTHROPIC_VERTEX_PROJECT_ID": "test-project",
        "CLOUD_ML_REGION": "us-east5",
        "CLAUDE_CODE_USE_VERTEX": "1",
        "GOOGLE_APPLICATION_CREDENTIALS": "/fake/path/creds.json",
    },
)
@patch("pr_filter.critique.run_claude_code")
def test_critique_pass_verdict_for_safe_change(mock_run_claude, config):
    """
    Given: PR with safe refactoring
    When: critique_pr() called
    Then: PASS verdict returned
    """
    mock_run_claude.return_value = {
        "comments": "",
        "summary": "This is a safe refactoring that improves code clarity without changing behavior.",
        "verdict": 1,
    }

    safe_pr = PullRequest(
        pr_number=12348,
        title="Refactor variable names",
        url="https://github.com/pytorch/pytorch/pull/12348",
        files_changed=["torch/_dynamo/utils.py"],
        diff="diff --git a/torch/_dynamo/utils.py ...",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user",
    )

    result = critique_pr(safe_pr, config)

    assert result.verdict == 1  # 1 = PASS
    assert result.comments == ""


@patch.dict(
    os.environ,
    {
        "ANTHROPIC_VERTEX_PROJECT_ID": "test-project",
        "CLOUD_ML_REGION": "us-east5",
        "CLAUDE_CODE_USE_VERTEX": "1",
        "GOOGLE_APPLICATION_CREDENTIALS": "/fake/path/creds.json",
    },
)
@patch("pr_filter.critique.run_claude_code")
def test_critique_default_pass_on_uncertainty(mock_run_claude, config):
    """
    Given: PR with ambiguous changes
    When: critique_pr() called
    Then: PASS verdict (default behavior when uncertain)
    """
    mock_run_claude.return_value = {
        "comments": "",
        "summary": "Cannot determine if this change introduces issues. Default to PASS.",
        "verdict": 1,
    }

    ambiguous_pr = PullRequest(
        pr_number=12349,
        title="Update logic",
        url="https://github.com/pytorch/pytorch/pull/12349",
        files_changed=["torch/_dynamo/convert.py"],
        diff="diff --git a/torch/_dynamo/convert.py ...",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user",
    )

    result = critique_pr(ambiguous_pr, config)

    assert result.verdict == 1  # 1 = PASS


@patch.dict(
    os.environ,
    {
        "ANTHROPIC_VERTEX_PROJECT_ID": "test-project",
        "CLOUD_ML_REGION": "us-east5",
        "CLAUDE_CODE_USE_VERTEX": "1",
        "GOOGLE_APPLICATION_CREDENTIALS": "/fake/path/creds.json",
    },
)
@patch("pr_filter.critique.run_claude_code")
def test_critique_explanation_format(mock_run_claude, sample_pr, config):
    """
    Given: PR with BLOCK verdict
    When: critique_pr() called
    Then: Comments include file, line, severity, category, message
    """
    mock_run_claude.return_value = {
        "comments": "Critical issue in torch/_dynamo/guards.py:42 - Modified guard generation to skip list mutation checks. "
        "Guard misses when VariableTracker wraps a mutated list. "
        "This fails when a VariableTracker wraps a list that gets mutated after guard creation. "
        "Suggestion: Add mutation tracking",
        "summary": "Critical correctness bug in guard generation",
        "verdict": 0,
    }

    result = critique_pr(sample_pr, config)

    assert result.verdict == 0  # 0 = BLOCK
    # Check comments contain key information
    assert "guards.py" in result.comments
    assert "42" in result.comments
    assert "Guard misses" in result.comments


@patch.dict(
    os.environ,
    {
        "ANTHROPIC_VERTEX_PROJECT_ID": "test-project",
        "CLOUD_ML_REGION": "us-east5",
        "CLAUDE_CODE_USE_VERTEX": "1",
        "GOOGLE_APPLICATION_CREDENTIALS": "/fake/path/creds.json",
    },
)
@patch("pr_filter.critique.run_claude_code")
def test_critique_loads_skills(mock_run_claude, sample_pr, config):
    """
    Given: Config with skill paths
    When: critique_pr() called
    Then: Skill paths referenced in prompt for Claude to Read if needed
    """
    config.skill_paths = ["skill1.md", "skill2.md"]

    mock_run_claude.return_value = {
        "comments": "",
        "summary": "No issues found",
        "verdict": 1,
    }

    critique_pr(sample_pr, config)

    # Verify Claude was called
    assert mock_run_claude.call_count == 1

    # Verify skill paths were included in prompt
    call_args = mock_run_claude.call_args
    prompt = call_args[0][0]  # First positional argument is the prompt
    assert "skill1.md" in prompt
    assert "skill2.md" in prompt
    assert "use Read tool" in prompt or "use the Read tool" in prompt
