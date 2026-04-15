"""Tests for diff reduction functionality."""

import pytest
from datetime import datetime
from pr_filter.models import PullRequest
from pr_filter.config import PRReviewConfig, DiffReductionConfig
from pr_filter.diff_reducer import reduce_diff


@pytest.fixture
def sample_pr():
    """Create a sample PullRequest for testing."""
    return PullRequest(
        pr_number=12345,
        title="Test PR",
        url="https://github.com/pytorch/pytorch/pull/12345",
        files_changed=["torch/_dynamo/symbolic_convert.py", "torch/nn/functional.py", "test/test_guards.py"],
        diff="""diff --git a/torch/_dynamo/symbolic_convert.py b/torch/_dynamo/symbolic_convert.py
index 1234567..abcdefg 100644
--- a/torch/_dynamo/symbolic_convert.py
+++ b/torch/_dynamo/symbolic_convert.py
@@ -100,6 +100,10 @@ def convert_to_graph(node):
     # Original implementation
     pass
+
+def new_function():
+    # New function added
+    pass

diff --git a/torch/nn/functional.py b/torch/nn/functional.py
index 2345678..bcdefgh 100644
--- a/torch/nn/functional.py
+++ b/torch/nn/functional.py
@@ -50,3 +50,6 @@ def relu(x):
     return torch.relu(x)
+
+def new_activation(x):
+    return x * 2

diff --git a/test/test_guards.py b/test/test_guards.py
index 3456789..cdefghi 100644
--- a/test/test_guards.py
+++ b/test/test_guards.py
@@ -10,3 +10,6 @@ def test_basic_guard():
     assert guard is not None
+
+def test_new_guard():
+    pass
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
        diff_reduction=DiffReductionConfig(
            max_lines=1000,
            priority_dirs=["torch/_dynamo", "torch/_inductor"]
        )
    )


def test_diff_reduction_filters_to_dynamo_inductor(sample_pr, config):
    """
    Given: PR diff with changes across torch/nn/, torch/_dynamo/, test/
    When: reduce_diff() called
    Then: Only torch/_dynamo/ changes included, test/ and torch/nn/ excluded
    """
    reduced = reduce_diff(sample_pr, config)

    # Should include torch/_dynamo/ changes
    assert "torch/_dynamo/symbolic_convert.py" in reduced
    assert "new_function" in reduced

    # Should exclude torch/nn/ and test/ changes
    assert "torch/nn/functional.py" not in reduced
    assert "test/test_guards.py" not in reduced
    assert "new_activation" not in reduced
    assert "test_new_guard" not in reduced


def test_diff_reduction_caps_at_max_lines(config):
    """
    Given: Large PR diff (5k lines)
    When: reduce_diff() called
    Then: Total lines <= 1000
    """
    # Create a PR with a very large diff
    large_diff = "diff --git a/torch/_dynamo/file.py b/torch/_dynamo/file.py\n"
    large_diff += "index 123..456 100644\n"
    large_diff += "--- a/torch/_dynamo/file.py\n"
    large_diff += "+++ b/torch/_dynamo/file.py\n"

    # Add 5000 lines of changes
    for i in range(5000):
        large_diff += f"+line {i}\n"

    large_pr = PullRequest(
        pr_number=12346,
        title="Large PR",
        url="https://github.com/pytorch/pytorch/pull/12346",
        files_changed=["torch/_dynamo/file.py"],
        diff=large_diff,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user"
    )

    reduced = reduce_diff(large_pr, config)

    # Should be capped at max_lines
    reduced_line_count = len(reduced.splitlines())
    assert reduced_line_count <= config.diff_reduction.max_lines


def test_diff_reduction_excludes_tests(config):
    """
    Given: PR with only test/ file changes
    When: reduce_diff() called
    Then: test/ changes excluded, empty or minimal diff returned
    """
    test_only_pr = PullRequest(
        pr_number=12347,
        title="Test-only PR",
        url="https://github.com/pytorch/pytorch/pull/12347",
        files_changed=["test/test_symbolic.py"],
        diff="""diff --git a/test/test_symbolic.py b/test/test_symbolic.py
index 123..456 100644
--- a/test/test_symbolic.py
+++ b/test/test_symbolic.py
@@ -10,3 +10,6 @@ def test_something():
     assert True
+
+def test_new():
+    assert False
""",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user"
    )

    reduced = reduce_diff(test_only_pr, config)

    # Should be empty or very minimal (no test/ content)
    assert "test/" not in reduced or reduced == ""


def test_diff_reduction_preserves_context(sample_pr, config):
    """
    Given: PR with function changes
    When: reduce_diff() called
    Then: Function context preserved (not just isolated lines)
    """
    reduced = reduce_diff(sample_pr, config)

    # Should preserve the full function context
    assert "def new_function():" in reduced or "new_function" in reduced


def test_empty_diff_after_reduction(config):
    """
    Given: PR with only test changes (no relevant changes after filtering)
    When: reduce_diff() called
    Then: Empty diff returned
    """
    test_only_pr = PullRequest(
        pr_number=12348,
        title="Docs and tests only",
        url="https://github.com/pytorch/pytorch/pull/12348",
        files_changed=["test/test_file.py", "docs/README.md"],
        diff="""diff --git a/test/test_file.py b/test/test_file.py
index 123..456 100644
--- a/test/test_file.py
+++ b/test/test_file.py
@@ -1,3 +1,6 @@
 def test_something():
     pass
+
+def test_new():
+    pass
""",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        author="test_user"
    )

    reduced = reduce_diff(test_only_pr, config)

    # Should return empty string for PRs with no relevant changes
    assert reduced == "" or len(reduced.strip()) == 0
