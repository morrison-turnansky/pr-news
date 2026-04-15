"""Integration tests for end-to-end pipeline."""

import pytest
import tempfile
import csv
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from pr_filter.config import load_config, PRReviewConfig


@pytest.fixture
def sample_csv():
    """Create a sample input CSV file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['pr_number', 'title', 'url', 'files_changed', 'state'])
        writer.writerow([
            12345,
            'Fix guard generation',
            'https://github.com/pytorch/pytorch/pull/12345',
            'torch/_dynamo/guards.py',
            'open'
        ])
        writer.writerow([
            12346,
            'Update scheduler',
            'https://github.com/pytorch/pytorch/pull/12346',
            'torch/_inductor/scheduler.py',
            'open'
        ])
        csv_path = f.name

    yield csv_path

    # Cleanup
    Path(csv_path).unlink()


@pytest.fixture
def test_config(sample_csv):
    """Create a test config YAML file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
        f.write(f"""repository: "pytorch/pytorch"
input_csv_path: "{sample_csv}"

diff_reduction:
  max_lines: 1000
  priority_dirs:
    - "torch/_dynamo"
    - "torch/_inductor"

model_params:
  temperature: 0.2
  max_tokens: 2000

skill_paths:
  - "skills/pr_critique.md"

self_check_enabled: false
""")
        config_path = f.name

    yield config_path

    # Cleanup
    Path(config_path).unlink()


def test_end_to_end_pipeline(sample_csv, test_config):
    """
    Given: CSV input with PRs
    When: Full pipeline executed (load → reduce diff → critique → generate front page)
    Then: CSV output produced with BLOCK verdicts only
    """
    # This is a placeholder test - full end-to-end would require mocking GitHub API and Vertex AI
    # For now, just verify config loading works
    config = load_config(test_config)

    assert config.repository == "pytorch/pytorch"
    assert config.input_csv_path == sample_csv
    assert config.diff_reduction.max_lines == 1000


@patch('sys.stdout')
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
    Given: config.yaml file
    When: load_config() called
    Then: PRReviewConfig loaded correctly with all settings
    """
    config = load_config(test_config)

    assert isinstance(config, PRReviewConfig)
    assert config.repository == "pytorch/pytorch"
    assert config.diff_reduction.max_lines == 1000
    assert len(config.diff_reduction.priority_dirs) == 2
    assert config.model_params.temperature == 0.2
    assert config.model_params.max_tokens == 2000
    assert config.self_check_enabled == False


@patch('pr_filter.critique.VertexAI')
def test_skill_integration(mock_vertex_class):
    """
    Given: Dynamo PR with critique
    When: critique runs
    Then: Explanation references Dynamo internals (VariableTracker, guards, etc.)
    """
    # Mock response that references Dynamo internals
    mock_vertex = Mock()
    mock_vertex.generate_content.return_value = """Verdict: BLOCK
Confidence: HIGH
Explanation: VariableTracker fails to track guard mutations in scheduler.py"""
    mock_vertex_class.return_value = mock_vertex

    # This would test that skill knowledge appears in critiques
    # Placeholder for now
    pass


@patch('pr_filter.critique.VertexAI')
def test_api_failure_handling(mock_vertex_class):
    """
    Given: Vertex AI rate limit error
    When: critique_pr() called
    Then: PR skipped, pipeline continues with remaining PRs
    """
    mock_vertex = Mock()
    mock_vertex.generate_content.side_effect = Exception("Rate limit exceeded")
    mock_vertex_class.return_value = mock_vertex

    # This would test that API failures don't crash the pipeline
    # Placeholder for now
    pass
