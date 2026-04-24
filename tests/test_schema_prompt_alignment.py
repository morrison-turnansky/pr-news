"""
Comprehensive verification that schema and prompt are fully aligned.

This test ensures:
1. Schema expects integers for verdict (0=BLOCK, 1=PASS)
2. Prompt tells Claude to use integers for verdict
3. Prompt examples validate against schema
4. No ambiguous patterns that could confuse Claude

Run this after modifying data_structs.py or prompts.py to verify
consistency.
"""

import json
import re
from datetime import datetime

from pr_filter.data_structs import PullRequest, ReviewOutputSchema, Verdict
from pr_filter.prompts import build_review_prompt, get_review_json_schema


def test_schema_verdict_is_integer():
    """Verify schema defines verdict as integer enum."""
    schema = get_review_json_schema()
    verdict_def = schema.get("$defs", {}).get("Verdict", {})

    assert verdict_def["type"] == "integer", "Verdict type should be integer"
    assert verdict_def["enum"] == [0, 1], "Verdict enum should be [0, 1]"


def test_prompt_instructs_integers():
    """Verify prompt tells Claude to use integers."""
    now = datetime.now()
    pr = PullRequest(
        pr_number=12345,
        title="Test",
        author="test",
        url="https://test.com",
        created_at=now,
        updated_at=now,
        files_changed=["test.py"],
        diff="diff",
    )

    prompt = build_review_prompt(pr, skill_paths=[])

    # Check for critical warnings
    checks = [
        (
            "verdict.*MUST be.*integer 0 or 1",
            "Critical warning about integer requirement",
        ),
        ("verdict: 0.*BLOCK", "Explanation that 0 = BLOCK"),
        ("verdict: 1.*PASS", "Explanation that 1 = PASS"),
    ]

    for pattern, desc in checks:
        assert re.search(pattern, prompt, re.IGNORECASE), f"Prompt missing: {desc}"


def test_prompt_example_uses_integers():
    """Verify prompt JSON example uses integer verdicts."""
    now = datetime.now()
    pr = PullRequest(
        pr_number=12345,
        title="Test",
        author="test",
        url="https://test.com",
        created_at=now,
        updated_at=now,
        files_changed=["test.py"],
        diff="diff",
    )

    prompt = build_review_prompt(pr, skill_paths=[])

    # Extract JSON example
    match = re.search(r"```json\n(\{.*?\})\n```", prompt, re.DOTALL)
    assert match, "Could not find JSON example in prompt"

    json_str = match.group(1).replace("{{", "{").replace("}}", "}")
    example = json.loads(json_str)

    # Check verdict values are integers
    summary_verdict = example["summary"]["verdict"]
    assert isinstance(
        summary_verdict, int
    ), f"Summary verdict should be int, got {type(summary_verdict)}"
    assert summary_verdict in [0, 1], f"Summary verdict should be 0 or 1, got {summary_verdict}"

    if example.get("comments"):
        comment_verdict = example["comments"][0]["verdict"]
        assert isinstance(
            comment_verdict, int
        ), f"Comment verdict should be int, got {type(comment_verdict)}"
        assert comment_verdict in [0, 1], f"Comment verdict should be 0 or 1, got {comment_verdict}"


def test_prompt_example_validates():
    """Verify prompt example validates against schema."""
    now = datetime.now()
    pr = PullRequest(
        pr_number=12345,
        title="Test",
        author="test",
        url="https://test.com",
        created_at=now,
        updated_at=now,
        files_changed=["test.py"],
        diff="diff",
    )

    prompt = build_review_prompt(pr, skill_paths=[])

    # Extract and validate example
    match = re.search(r"```json\n(\{.*?\})\n```", prompt, re.DOTALL)
    json_str = match.group(1).replace("{{", "{").replace("}}", "}")
    example = json.loads(json_str)

    result = ReviewOutputSchema.model_validate(example)

    assert result.summary.verdict == Verdict.BLOCK, "Example should show BLOCK verdict"
    assert result.summary.verdict.value == 0, "BLOCK should have value 0"


def test_no_string_verdicts_in_prompt():
    """Verify prompt does NOT tell Claude to use string verdicts."""
    now = datetime.now()
    pr = PullRequest(
        pr_number=12345,
        title="Test",
        author="test",
        url="https://test.com",
        created_at=now,
        updated_at=now,
        files_changed=["test.py"],
        diff="diff",
    )

    prompt = build_review_prompt(pr, skill_paths=[])

    # Check for bad patterns (string verdicts in JSON)
    bad_patterns = [
        r'"verdict":\s*"BLOCK"',
        r'"verdict":\s*"PASS"',
        r'"verdict":\s*"block"',
        r'"verdict":\s*"pass"',
        r'"verdict":\s*"BLOCK\|PASS"',
    ]

    for pattern in bad_patterns:
        assert not re.search(pattern, prompt), f"Prompt contains bad pattern: {pattern}"


def test_no_ambiguous_field_patterns():
    """Verify prompt doesn't have ambiguous field value patterns."""
    now = datetime.now()
    pr = PullRequest(
        pr_number=12345,
        title="Test",
        author="test",
        url="https://test.com",
        created_at=now,
        updated_at=now,
        files_changed=["test.py"],
        diff="diff",
    )

    prompt = build_review_prompt(pr, skill_paths=[])

    # Extract JSON example
    match = re.search(r"```json\n(\{.*?\})\n```", prompt, re.DOTALL)
    json_example = match.group(1)

    # Check for pipe-separated values (like "critical|major|minor")
    bad_patterns = [
        (r'"severity":\s*"[^"]*\|[^"]*"', "severity with pipes"),
        (r'"category":\s*"[^"]*\|[^"]*"', "category with pipes"),
    ]

    for pattern, desc in bad_patterns:
        assert not re.search(pattern, json_example), f"Found {desc} in JSON example"


def test_common_outputs_validate():
    """Verify common output patterns validate correctly."""
    test_cases = [
        (
            "PASS with no issues",
            {
                "comments": [],
                "summary": {
                    "total_issues": 0,
                    "critical": 0,
                    "major": 0,
                    "minor": 0,
                    "suggestions": 0,
                    "verdict": 1,
                    "explanation": "No issues found",
                },
            },
        ),
        (
            "BLOCK with critical issue",
            {
                "comments": [
                    {
                        "file": "torch/file.py",
                        "line": 10,
                        "severity": "critical",
                        "category": "correctness",
                        "message": "Bug found",
                        "suggestion": "Fix it",
                        "verdict": 0,
                    }
                ],
                "summary": {
                    "total_issues": 1,
                    "critical": 1,
                    "major": 0,
                    "minor": 0,
                    "suggestions": 0,
                    "verdict": 0,
                    "explanation": "Critical bug found",
                },
            },
        ),
    ]

    for desc, test_json in test_cases:
        result = ReviewOutputSchema.model_validate(test_json)
        assert result.summary.verdict in [
            Verdict.BLOCK,
            Verdict.PASS,
        ], f"{desc} should have valid verdict"
