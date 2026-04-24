"""Tests for Pydantic schema generation."""

import json

import pytest
from pydantic import ValidationError

from pr_filter.data_structs import ReviewComment, ReviewOutputSchema, ReviewSummary, Verdict
from pr_filter.prompts import get_review_json_schema


def test_review_comment_schema_valid():
    """Test that valid ReviewComment data passes validation."""
    valid_data = {
        "file": "torch/_dynamo/guards.py",
        "line": 42,
        "severity": "critical",
        "category": "correctness",
        "message": "This is a bug",
        "suggestion": "Fix it like this",
        "verdict": 0,  # Integer: 0 = BLOCK
    }

    comment = ReviewComment(**valid_data)
    assert comment.file == "torch/_dynamo/guards.py"
    assert comment.line == 42
    assert comment.severity == "critical"
    assert comment.verdict == Verdict.BLOCK


def test_review_comment_schema_invalid_severity():
    """Test that invalid severity value is rejected."""
    invalid_data = {
        "file": "test.py",
        "line": 1,
        "severity": "invalid_severity",  # Not in pattern
        "category": "correctness",
        "message": "Test",
        "verdict": 1,  # Integer: 1 = PASS
    }

    with pytest.raises(ValidationError) as exc_info:
        ReviewComment(**invalid_data)

    # Verify the error mentions the severity field
    assert "severity" in str(exc_info.value)


def test_review_comment_schema_invalid_verdict():
    """Test that invalid verdict value is rejected."""
    invalid_data = {
        "file": "test.py",
        "line": 1,
        "severity": "critical",
        "category": "correctness",
        "message": "Test",
        "verdict": 99,  # Invalid: must be 0 or 1
    }

    with pytest.raises(ValidationError) as exc_info:
        ReviewComment(**invalid_data)

    assert "verdict" in str(exc_info.value)


def test_review_comment_schema_negative_line():
    """Test that negative line numbers are rejected."""
    invalid_data = {
        "file": "test.py",
        "line": -1,  # Must be >= 0
        "severity": "critical",
        "category": "correctness",
        "message": "Test",
        "verdict": 0,
    }

    with pytest.raises(ValidationError) as exc_info:
        ReviewComment(**invalid_data)

    assert "line" in str(exc_info.value)


def test_review_comment_schema_optional_suggestion():
    """Test that suggestion field is optional."""
    data = {
        "file": "test.py",
        "line": 1,
        "severity": "minor",
        "category": "style",
        "message": "Test",
        "verdict": 1,  # Integer: 1 = PASS
        # suggestion omitted
    }

    comment = ReviewComment(**data)
    assert comment.suggestion == ""  # Default value


def test_review_summary_schema_valid():
    """Test that valid ReviewSummary data passes validation."""
    valid_data = {
        "total_issues": 5,
        "critical": 1,
        "major": 2,
        "minor": 1,
        "suggestions": 1,
        "verdict": 0,  # Integer: 0 = BLOCK
        "explanation": "Found critical bugs",
    }

    summary = ReviewSummary(**valid_data)
    assert summary.total_issues == 5
    assert summary.critical == 1
    assert summary.verdict == Verdict.BLOCK


def test_review_summary_schema_negative_counts():
    """Test that negative issue counts are rejected."""
    invalid_data = {
        "total_issues": -1,  # Must be >= 0
        "critical": 0,
        "major": 0,
        "minor": 0,
        "suggestions": 0,
        "verdict": 1,  # Integer: 1 = PASS
        "explanation": "Test",
    }

    with pytest.raises(ValidationError) as exc_info:
        ReviewSummary(**invalid_data)

    assert "total_issues" in str(exc_info.value)


def test_review_output_schema_valid():
    """Test that valid complete review output passes validation."""
    valid_data = {
        "comments": [
            {
                "file": "test.py",
                "line": 42,
                "severity": "critical",
                "category": "correctness",
                "message": "Bug found",
                "verdict": 0,  # Integer: 0 = BLOCK
            }
        ],
        "summary": {
            "total_issues": 1,
            "critical": 1,
            "major": 0,
            "minor": 0,
            "suggestions": 0,
            "verdict": 0,  # Integer: 0 = BLOCK
            "explanation": "Critical bug detected",
        },
    }

    output = ReviewOutputSchema(**valid_data)
    assert len(output.comments) == 1
    assert output.summary.verdict == Verdict.BLOCK


def test_review_output_schema_empty_comments():
    """Test that empty comments list is valid."""
    valid_data = {
        "comments": [],  # Empty list is valid
        "summary": {
            "total_issues": 0,
            "critical": 0,
            "major": 0,
            "minor": 0,
            "suggestions": 0,
            "verdict": 1,  # Integer: 1 = PASS
            "explanation": "No issues",
        },
    }

    output = ReviewOutputSchema(**valid_data)
    assert len(output.comments) == 0
    assert output.summary.verdict == Verdict.PASS


def test_get_review_json_schema_structure():
    """Test that generated JSON schema has expected structure."""
    schema = get_review_json_schema()

    # Should be a dict with standard JSON Schema fields
    assert isinstance(schema, dict)
    assert "type" in schema
    assert schema["type"] == "object"

    # Should have properties
    assert "properties" in schema
    assert "comments" in schema["properties"]
    assert "summary" in schema["properties"]

    # Should have required fields
    assert "required" in schema
    assert "summary" in schema["required"]

    # Should have definitions for nested objects
    assert "$defs" in schema
    assert "ReviewComment" in schema["$defs"]
    assert "ReviewSummary" in schema["$defs"]


def test_get_review_json_schema_serializable():
    """Test that generated schema can be serialized to JSON."""
    schema = get_review_json_schema()

    # Should be JSON-serializable
    json_str = json.dumps(schema)
    assert isinstance(json_str, str)

    # Should be deserializable
    parsed = json.loads(json_str)
    assert parsed == schema


def test_review_comment_schema_has_patterns():
    """Test that schema includes regex patterns for validation."""
    schema = get_review_json_schema()

    # Get ReviewComment definition
    comment_schema = schema["$defs"]["ReviewComment"]

    # Should have pattern for severity
    assert "pattern" in comment_schema["properties"]["severity"]
    assert "critical|major|minor|suggestion" in comment_schema["properties"]["severity"]["pattern"]

    # Should have pattern for category
    assert "pattern" in comment_schema["properties"]["category"]
    assert (
        "correctness|performance|security|style"
        in comment_schema["properties"]["category"]["pattern"]
    )

    # Verdict should be a reference to the Verdict enum (integer enum)
    assert "$ref" in comment_schema["properties"]["verdict"]
    assert comment_schema["properties"]["verdict"]["$ref"] == "#/$defs/Verdict"

    # Verify Verdict enum definition
    verdict_schema = schema["$defs"]["Verdict"]
    assert verdict_schema["type"] == "integer"
    assert verdict_schema["enum"] == [0, 1]


def test_review_summary_schema_has_minimum():
    """Test that schema includes minimum constraints for integers."""
    schema = get_review_json_schema()

    # Get ReviewSummary definition
    summary_schema = schema["$defs"]["ReviewSummary"]

    # Should have minimum: 0 for all count fields
    for field in ["total_issues", "critical", "major", "minor", "suggestions"]:
        assert "minimum" in summary_schema["properties"][field]
        assert summary_schema["properties"][field]["minimum"] == 0


def test_review_comment_schema_line_has_minimum():
    """Test that line field has minimum constraint."""
    schema = get_review_json_schema()

    comment_schema = schema["$defs"]["ReviewComment"]
    assert "minimum" in comment_schema["properties"]["line"]
    assert comment_schema["properties"]["line"]["minimum"] == 0


def test_schema_has_descriptions():
    """Test that schema includes field descriptions."""
    schema = get_review_json_schema()

    comment_schema = schema["$defs"]["ReviewComment"]
    summary_schema = schema["$defs"]["ReviewSummary"]

    # Comment fields should have descriptions
    assert "description" in comment_schema["properties"]["file"]
    assert "description" in comment_schema["properties"]["message"]

    # Summary fields should have descriptions
    assert "description" in summary_schema["properties"]["verdict"]
    assert "description" in summary_schema["properties"]["explanation"]
