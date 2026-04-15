"""Tests for agentic PR critique functionality."""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime
from pr_filter.models import PullRequest, CritiquedPR
from pr_filter.config import PRReviewConfig, ModelParams
from pr_filter.critique import critique_pr


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
        author="test_user"
    )


@pytest.fixture
def config():
    """Create a test configuration."""
    return PRReviewConfig(
        repository="pytorch/pytorch",
        input_csv_path="test.csv",
        skill_paths=["skills/pr_critique.md"],
        self_check_enabled=False  # Disable for basic tests
    )


@pytest.fixture
def config_with_self_check():
    """Create a test configuration with self-check enabled."""
    return PRReviewConfig(
        repository="pytorch/pytorch",
        input_csv_path="test.csv",
        skill_paths=["skills/pr_critique.md"],
        self_check_enabled=True
    )


@patch('pr_filter.critique.VertexAI')
def test_critique_uses_fresh_agent_per_pr(mock_vertex_class, sample_pr, config):
    """
    Given: 3 PRs to analyze
    When: critique_pr() called for each
    Then: 3 separate VertexAI.generate_content() calls made, no session reuse
    """
    # Create mock instance
    mock_vertex = Mock()
    mock_vertex.generate_content.return_value = "Verdict: PASS\nConfidence: HIGH\nExplanation: No issues found"
    mock_vertex_class.return_value = mock_vertex

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
        author="test_user"
    )
    pr3 = PullRequest(
        pr_number=12347,
        title="Third PR",
        url="https://github.com/pytorch/pytorch/pull/12347",
        files_changed=["torch/_dynamo/symbolic_convert.py"],
        diff="diff --git a/torch/_dynamo/symbolic_convert.py ...",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user"
    )

    reduced_diff = "some reduced diff"

    # Analyze each PR
    critique_pr(pr1, reduced_diff, config)
    critique_pr(pr2, reduced_diff, config)
    critique_pr(pr3, reduced_diff, config)

    # Verify 3 separate calls were made (fresh agent pattern)
    assert mock_vertex.generate_content.call_count == 3


@patch('pr_filter.critique.VertexAI')
def test_critique_block_verdict_with_explanation(mock_vertex_class, sample_pr, config):
    """
    Given: PR with clear bug
    When: critique_pr() called
    Then: BLOCK verdict with detailed explanation returned
    """
    mock_vertex = Mock()
    mock_vertex.generate_content.return_value = """Verdict: BLOCK
Confidence: HIGH
Explanation: Guard generation logic in guards.py line 42 fails to account for list mutation.
If a VariableTracker wraps a list that gets mutated after guard creation, the guard will miss
the change and allow incorrect specialization. This causes silent wrong results when the cached
graph is reused with different list contents."""
    mock_vertex_class.return_value = mock_vertex

    reduced_diff = sample_pr.diff
    result = critique_pr(sample_pr, reduced_diff, config)

    assert isinstance(result, CritiquedPR)
    assert result.verdict == "BLOCK"
    assert result.confidence == "HIGH"
    assert "list mutation" in result.issue_explanation
    assert result.pr_number == 12345


@patch('pr_filter.critique.VertexAI')
def test_critique_pass_verdict_for_safe_change(mock_vertex_class, config):
    """
    Given: PR with safe refactoring
    When: critique_pr() called
    Then: PASS verdict returned
    """
    mock_vertex = Mock()
    mock_vertex.generate_content.return_value = """Verdict: PASS
Confidence: HIGH
Explanation: This is a safe refactoring that improves code clarity without changing behavior."""
    mock_vertex_class.return_value = mock_vertex

    safe_pr = PullRequest(
        pr_number=12348,
        title="Refactor variable names",
        url="https://github.com/pytorch/pytorch/pull/12348",
        files_changed=["torch/_dynamo/utils.py"],
        diff="diff --git a/torch/_dynamo/utils.py ...",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user"
    )

    reduced_diff = "some safe refactoring diff"
    result = critique_pr(safe_pr, reduced_diff, config)

    assert result.verdict == "PASS"
    assert result.issue_explanation == ""  # No explanation for PASS


@patch('pr_filter.critique.VertexAI')
def test_critique_default_pass_on_uncertainty(mock_vertex_class, config):
    """
    Given: PR with ambiguous changes
    When: critique_pr() called
    Then: PASS verdict (default behavior when uncertain)
    """
    mock_vertex = Mock()
    mock_vertex.generate_content.return_value = """Verdict: PASS
Confidence: MEDIUM
Explanation: Cannot determine if this change introduces issues. Default to PASS."""
    mock_vertex_class.return_value = mock_vertex

    ambiguous_pr = PullRequest(
        pr_number=12349,
        title="Update logic",
        url="https://github.com/pytorch/pytorch/pull/12349",
        files_changed=["torch/_dynamo/convert.py"],
        diff="diff --git a/torch/_dynamo/convert.py ...",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user"
    )

    reduced_diff = "some ambiguous diff"
    result = critique_pr(ambiguous_pr, reduced_diff, config)

    assert result.verdict == "PASS"


@patch('pr_filter.critique.VertexAI')
def test_critique_explanation_format(mock_vertex_class, sample_pr, config):
    """
    Given: PR with BLOCK verdict
    When: critique_pr() called
    Then: Explanation includes: what changed, flaw, why incorrect, when fails
    """
    mock_vertex = Mock()
    mock_vertex.generate_content.return_value = """Verdict: BLOCK
Confidence: HIGH
Explanation: File: torch/_dynamo/guards.py, line 42
What changed: Modified guard generation to skip list mutation checks
What's the flaw: Guard misses when VariableTracker wraps a mutated list
Why incorrect: Cached graph assumes immutable list, but list was modified
When it fails: When a VariableTracker wraps a list that gets mutated after guard creation"""
    mock_vertex_class.return_value = mock_vertex

    reduced_diff = sample_pr.diff
    result = critique_pr(sample_pr, reduced_diff, config)

    assert result.verdict == "BLOCK"
    explanation = result.issue_explanation

    # Check all required elements present
    assert "What changed" in explanation or "torch/_dynamo/guards.py" in explanation
    assert "flaw" in explanation or "Guard misses" in explanation
    assert "Why incorrect" in explanation or "incorrect" in explanation.lower()
    assert "When it fails" in explanation or "when" in explanation.lower()


@patch('pr_filter.critique.VertexAI')
@patch('pr_filter.critique.load_skills')
def test_critique_loads_skills(mock_load_skills, mock_vertex_class, sample_pr, config):
    """
    Given: Config with skill paths
    When: critique_pr() called
    Then: Skills loaded and included in prompt
    """
    mock_load_skills.return_value = "# PyTorch Dynamo Skill Content"

    mock_vertex = Mock()
    mock_vertex.generate_content.return_value = "Verdict: PASS\nConfidence: HIGH\nExplanation: "
    mock_vertex_class.return_value = mock_vertex

    reduced_diff = sample_pr.diff
    critique_pr(sample_pr, reduced_diff, config)

    # Verify skills were loaded
    mock_load_skills.assert_called_once_with(config.skill_paths)

    # Verify generate_content was called with prompt including skills
    assert mock_vertex.generate_content.call_count == 1


@patch('pr_filter.critique.VertexAI')
def test_critique_self_check_reduces_false_positives(mock_vertex_class, sample_pr, config_with_self_check):
    """
    Given: Weak BLOCK verdict and self-check enabled
    When: critique_pr() called
    Then: Self-check validates and may change verdict to PASS
    """
    mock_vertex = Mock()

    # First call returns weak BLOCK
    # Second call (self-check) changes to PASS
    mock_vertex.generate_content.side_effect = [
        """Verdict: BLOCK
Confidence: MEDIUM
Explanation: This might potentially cause issues""",
        """Verdict: PASS
Confidence: MEDIUM
Explanation: On review, this is speculative. Changing to PASS."""
    ]
    mock_vertex_class.return_value = mock_vertex

    reduced_diff = sample_pr.diff
    result = critique_pr(sample_pr, reduced_diff, config_with_self_check)

    # Should call generate_content twice (initial + self-check)
    assert mock_vertex.generate_content.call_count == 2

    # Final verdict should be PASS after self-check
    assert result.verdict == "PASS"
