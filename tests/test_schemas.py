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


def test_review_comment_accepts_any_severity():
    """Test that severity field accepts any string (no pattern constraint)."""
    # Patterns are not supported by Claude structured outputs
    # We accept any string and rely on Claude to follow instructions
    data = {
        "file": "test.py",
        "line": 1,
        "severity": "custom_severity",
        "category": "correctness",
        "message": "Test",
        "verdict": 1,
    }
    comment = ReviewComment(**data)
    assert comment.severity == "custom_severity"


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


def test_review_comment_accepts_any_line():
    """Test that line field accepts any integer (no minimum constraint)."""
    # Minimum constraints are not supported by Claude structured outputs
    data = {
        "file": "test.py",
        "line": -1,
        "severity": "critical",
        "category": "correctness",
        "message": "Test",
        "verdict": 0,
    }
    comment = ReviewComment(**data)
    assert comment.line == -1


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


def test_review_summary_accepts_any_counts():
    """Test that count fields accept any integer (no minimum constraint)."""
    # Minimum constraints are not supported by Claude structured outputs
    data = {
        "total_issues": -1,
        "critical": 0,
        "major": 0,
        "minor": 0,
        "suggestions": 0,
        "verdict": 1,
        "explanation": "Test",
    }
    summary = ReviewSummary(**data)
    assert summary.total_issues == -1


def test_review_output_schema_valid():
    """Test that valid complete review output passes validation (simplified schema)."""
    valid_data = {
        "comments": "Critical issue in test.py:42 - Bug found",
        "summary": "Critical bug detected",
        "verdict": 0,  # Integer: 0 = BLOCK
    }

    output = ReviewOutputSchema(**valid_data)
    assert "Bug found" in output.comments
    assert output.verdict == 0


def test_review_output_schema_empty_comments():
    """Test that empty comments string is valid (simplified schema)."""
    valid_data = {
        "comments": "",  # Empty string is valid
        "summary": "No issues",
        "verdict": 1,  # Integer: 1 = PASS
    }

    output = ReviewOutputSchema(**valid_data)
    assert output.comments == ""
    assert output.verdict == 1


def test_get_review_json_schema_structure():
    """Test that generated JSON schema has expected structure (simplified schema)."""
    schema = get_review_json_schema()

    # Should be a dict with standard JSON Schema fields
    assert isinstance(schema, dict)
    assert "type" in schema
    assert schema["type"] == "object"

    # Should have properties
    assert "properties" in schema
    assert "comments" in schema["properties"]
    assert "summary" in schema["properties"]
    assert "verdict" in schema["properties"]

    # Verify field types
    assert schema["properties"]["comments"]["type"] == "string"
    assert schema["properties"]["summary"]["type"] == "string"
    assert schema["properties"]["verdict"]["type"] == "integer"


def test_get_review_json_schema_serializable():
    """Test that generated schema can be serialized to JSON."""
    schema = get_review_json_schema()

    # Should be JSON-serializable
    json_str = json.dumps(schema)
    assert isinstance(json_str, str)

    # Should be deserializable
    parsed = json.loads(json_str)
    assert parsed == schema


def test_review_output_schema_verdict_is_integer():
    """Test that verdict is an integer type (simplified schema)."""
    schema = get_review_json_schema()

    # Verdict should be integer type (not enum reference since simplified)
    verdict_prop = schema["properties"]["verdict"]
    assert verdict_prop["type"] == "integer"
    assert verdict_prop["default"] == 1


def test_schema_has_descriptions():
    """Test that schema includes field descriptions (simplified schema)."""
    schema = get_review_json_schema()

    # Output schema fields should have descriptions
    assert "description" in schema["properties"]["comments"]
    assert "description" in schema["properties"]["summary"]
    assert "description" in schema["properties"]["verdict"]
