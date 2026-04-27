"""
Comprehensive verification that schema and prompt are fully aligned (simplified schema).

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

from pr_filter.data_structs import PullRequest, ReviewOutputSchema
from pr_filter.prompts import build_review_prompt, get_review_json_schema


def test_schema_verdict_is_integer():
    """Verify schema defines verdict as integer."""
    schema = get_review_json_schema()
    verdict_prop = schema["properties"]["verdict"]

    assert verdict_prop["type"] == "integer", "Verdict type should be integer"
    assert verdict_prop["default"] == 1, "Verdict default should be 1 (PASS)"


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
    """Verify prompt JSON example uses integer verdict (simplified schema)."""
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

    # Check verdict value is integer
    verdict = example["verdict"]
    assert isinstance(verdict, int), f"Verdict should be int, got {type(verdict)}"
    assert verdict in [0, 1], f"Verdict should be 0 or 1, got {verdict}"


def test_prompt_example_validates():
    """Verify prompt example validates against schema (simplified schema)."""
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

    assert result.verdict == 0, "Example should show BLOCK verdict (0)"


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
    """Verify prompt doesn't have ambiguous field value patterns (simplified schema)."""
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

    # Check verdict is integer (not string with pipes)
    assert not re.search(
        r'"verdict":\s*"[^"]*\|[^"]*"', json_example
    ), "Found verdict with pipes in JSON example"


def test_common_outputs_validate():
    """Verify common output patterns validate correctly (simplified schema)."""
    test_cases = [
        (
            "PASS with no issues",
            {
                "comments": "",
                "summary": "No issues found",
                "verdict": 1,
            },
        ),
        (
            "BLOCK with critical issue",
            {
                "comments": "Critical bug in torch/file.py:10 - Bug found. Fix it.",
                "summary": "Critical bug found",
                "verdict": 0,
            },
        ),
    ]

    for desc, test_json in test_cases:
        result = ReviewOutputSchema.model_validate(test_json)
        assert result.verdict in [0, 1], f"{desc} should have valid verdict"
