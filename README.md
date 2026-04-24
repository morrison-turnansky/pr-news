# PyTorch PR Review Filter

AI-assisted PR review filter for PyTorch torch.compile. Analyzes PRs to detect critical bugs in Dynamo and Inductor using Claude Code agent via Google Vertex AI.

**Design Philosophy**: Precision over recall — minimize false positives, default to PASS.

## Usage

Fetch and analyze PyTorch PRs from GitHub API. Filter by label, author, and date range. Claude Code agent explores the codebase with tools (Read, Grep) to produce structured reviews.

```bash
# Authenticate with gcloud (one-time setup)
gcloud auth application-default login

# Set required environment variables (already configured in devcontainer.json)
export GH_TOKEN="ghp_xxxxxxxxxxxx"
export ANTHROPIC_VERTEX_PROJECT_ID="project_id"
export CLOUD_ML_REGION="region"
export CLAUDE_CODE_USE_VERTEX="1"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"

# Run analysis on dynamo PRs from specific date range
python end_to_end.py
```

Output shows BLOCK verdicts only (critical bugs detected):

```
[1/15] Analyzing PR #180389: [dynamo] Allow tracing into _maybe_view_chunk_cat
  Diff size: 46 lines
  ✓ Verdict: PASS

BLOCKED: 0
PASSED: 15
```

Results are exported to `pr_analysis_results.json` with structured review data.

## Installation

```bash
# Install package
uv pip install -e .

# Install with dev dependencies (linting, testing, pre-commit)
uv pip install -e ".[dev]"
```

**Requirements**:
- Python 3.13+
- Google Cloud Vertex AI access with Claude enabled
- GitHub token (GH_TOKEN)

## Linting

Pre-commit hooks run automatically on `git commit`:

```bash
# Install pre-commit hooks (automatic with dev install)
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Lint only
ruff check .

# Auto-fix and format
ruff check --fix .
ruff format .

# Type check
pyrefly check .
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_critique.py -v

# With coverage
pytest tests/ --cov=pr_filter --cov-report=html
```
