"""Integration tests for end-to-end pipeline."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pr_filter.config import PRReviewConfig, load_config


@pytest.fixture
def test_config():
    """Create a test config JSON file."""
    config_data = {
        "repository": "pytorch/pytorch",
        "workspace_path": "/workspace/pytorch",
        "skill_paths": ["skills/pr_critique.md"],
        "filter": {"labels": ["module: dynamo"], "authors": []},
    }

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_data, f, indent=2)
        config_path = f.name

    yield config_path

    # Cleanup
    Path(config_path).unlink()


def test_end_to_end_pipeline():
    """
    Given: GitHub API filter criteria
    When: Full pipeline executed (fetch → critique → export JSON)
    Then: JSON output produced with BLOCK verdicts only
    """
    # This is a placeholder test - full end-to-end would require mocking GitHub API and Vertex AI
    # For now, just verify the pipeline components are importable
    from pr_filter.critique import critique_pr
    from pr_filter.filter import fetch_prs
    from pr_filter.output import export_json

    assert callable(fetch_prs)
    assert callable(critique_pr)
    assert callable(export_json)


@patch("sys.stdout")
def test_stdout_logging(mock_stdout):
    """
    Given: PRs being analyzed
    When: Pipeline runs
    Then: Stdout contains progress messages for each PR
    """
    # This test would verify stdout logging in the actual CLI
    # For now, it's a placeholder
    pass


def test_config_loading(test_config):
    """
    Given: config.json file
    When: load_config() called
    Then: PRReviewConfig loaded correctly with all settings
    """
    config = load_config(test_config)

    assert isinstance(config, PRReviewConfig)
    assert config.repository == "pytorch/pytorch"
    assert len(config.skill_paths) > 0
    assert config.filter_config.repo == "pytorch/pytorch"
