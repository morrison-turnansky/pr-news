"""Tests for front page generator functionality."""

import pytest
import tempfile
import csv
from datetime import datetime
from pathlib import Path
from pr_filter.models import CritiquedPR, FrontPage, SummaryStats
from pr_filter.config import PRReviewConfig
from pr_filter.generator import generate_front_page, export_csv


@pytest.fixture
def critiqued_prs():
    """Create a list of CritiquedPR objects for testing."""
    base_time = datetime.now()

    return [
        # BLOCK verdicts
        CritiquedPR(
            pr_number=12345,
            title="Fix guard generation bug",
            url="https://github.com/pytorch/pytorch/pull/12345",
            files_changed=["torch/_dynamo/guards.py"],
            diff="diff content",
            created_at=base_time,
            updated_at=base_time,
            author="user1",
            verdict="BLOCK",
            confidence="HIGH",
            issue_explanation="Critical bug in guard generation",
            reduced_diff_lines=100
        ),
        CritiquedPR(
            pr_number=12346,
            title="Update scheduler",
            url="https://github.com/pytorch/pytorch/pull/12346",
            files_changed=["torch/_inductor/scheduler.py"],
            diff="diff content",
            created_at=base_time,
            updated_at=base_time,
            author="user2",
            verdict="BLOCK",
            confidence="MEDIUM",
            issue_explanation="Fusion logic assumes contiguous inputs",
            reduced_diff_lines=150
        ),
        CritiquedPR(
            pr_number=12347,
            title="Add optimization",
            url="https://github.com/pytorch/pytorch/pull/12347",
            files_changed=["torch/_inductor/codegen.py"],
            diff="diff content",
            created_at=base_time,
            updated_at=base_time,
            author="user3",
            verdict="BLOCK",
            confidence="HIGH",
            issue_explanation="Codegen produces wrong Triton code",
            reduced_diff_lines=200
        ),
        # PASS verdicts
        CritiquedPR(
            pr_number=12348,
            title="Refactor utils",
            url="https://github.com/pytorch/pytorch/pull/12348",
            files_changed=["torch/_dynamo/utils.py"],
            diff="diff content",
            created_at=base_time,
            updated_at=base_time,
            author="user4",
            verdict="PASS",
            confidence="HIGH",
            issue_explanation="",
            reduced_diff_lines=50
        ),
        CritiquedPR(
            pr_number=12349,
            title="Update docs",
            url="https://github.com/pytorch/pytorch/pull/12349",
            files_changed=["docs/compile.md"],
            diff="diff content",
            created_at=base_time,
            updated_at=base_time,
            author="user5",
            verdict="PASS",
            confidence=None,
            issue_explanation="",
            reduced_diff_lines=20
        ),
    ]


@pytest.fixture
def config():
    """Create test configuration."""
    return PRReviewConfig(
        repository="pytorch/pytorch",
        input_csv_path="test.csv"
    )


def test_binary_filter_blocks_only(critiqued_prs):
    """
    Given: List of CritiquedPR with mix of BLOCK and PASS verdicts
    When: generate_front_page() called
    Then: Only BLOCK verdicts in output, PASS verdicts discarded
    """
    front_page = generate_front_page(critiqued_prs)

    # Should have exactly 3 BLOCK verdicts
    assert len(front_page.blocked_prs) == 3

    # All should be BLOCK verdicts
    for pr in front_page.blocked_prs:
        assert pr.verdict == "BLOCK"

    # PASS verdicts should not be included
    pr_numbers = [pr.pr_number for pr in front_page.blocked_prs]
    assert 12348 not in pr_numbers  # PASS verdict
    assert 12349 not in pr_numbers  # PASS verdict


def test_csv_output_columns(critiqued_prs, config):
    """
    Given: FrontPage with BLOCK verdicts
    When: export_csv() called
    Then: CSV has all required columns
    """
    front_page = generate_front_page(critiqued_prs)

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        output_path = f.name

    try:
        export_csv(front_page, output_path)

        # Read CSV and check columns
        with open(output_path, 'r') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            # Check required columns present
            assert 'pr_number' in headers
            assert 'title' in headers
            assert 'url' in headers
            assert 'verdict' in headers
            assert 'confidence' in headers
            assert 'issue_explanation' in headers

            # Check data
            rows = list(reader)
            assert len(rows) == 3  # 3 BLOCK verdicts
    finally:
        # Cleanup
        Path(output_path).unlink()


def test_csv_sorting_by_confidence(critiqued_prs):
    """
    Given: BLOCK verdicts with different confidence levels
    When: generate_front_page() called with sorting
    Then: HIGH confidence PRs sorted first, then MEDIUM
    """
    front_page = generate_front_page(critiqued_prs)
    front_page.sort_by_confidence()

    # First two should be HIGH confidence
    assert front_page.blocked_prs[0].confidence == "HIGH"
    assert front_page.blocked_prs[1].confidence == "HIGH"

    # Third should be MEDIUM confidence
    assert front_page.blocked_prs[2].confidence == "MEDIUM"


def test_empty_front_page():
    """
    Given: All PASS verdicts (no BLOCK)
    When: generate_front_page() called
    Then: Empty front page with 0 blocked PRs
    """
    pass_only_prs = [
        CritiquedPR(
            pr_number=12350,
            title="Safe change",
            url="https://github.com/pytorch/pytorch/pull/12350",
            files_changed=["torch/_dynamo/file.py"],
            diff="diff",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            author="user",
            verdict="PASS",
            confidence="HIGH",
            issue_explanation="",
            reduced_diff_lines=10
        )
    ]

    front_page = generate_front_page(pass_only_prs)

    assert len(front_page.blocked_prs) == 0
    assert front_page.summary_stats.blocked_count == 0
    assert front_page.summary_stats.passed_count == 1


def test_summary_stats(critiqued_prs):
    """
    Given: Mix of BLOCK and PASS verdicts
    When: generate_front_page() called
    Then: Summary stats show correct counts
    """
    front_page = generate_front_page(critiqued_prs)

    assert front_page.summary_stats.blocked_count == 3
    assert front_page.summary_stats.passed_count == 2
    assert front_page.summary_stats.total_analyzed == 5
    assert front_page.summary_stats.block_rate == 60.0  # 3/5 = 60%
