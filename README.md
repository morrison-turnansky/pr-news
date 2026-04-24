# PR Review Filter

AI-assisted PR review filter that detects critical bugs using Claude Code agent via Google Vertex AI.

**Design Philosophy**: Precision over recall — minimize false positives, default to PASS.

## Usage

Fetch and analyze PRs from GitHub API. Filter by label, author, and date range. Claude Code agent explores the codebase with tools (Read, Grep) to produce structured reviews with domain-specific guidance.

```bash
# Authenticate with gcloud (one-time setup)
gcloud auth application-default login

# Set required environment variables (already configured in devcontainer.json)
export GH_TOKEN="ghp_xxxxxxxxxxxx"
export ANTHROPIC_VERTEX_PROJECT_ID="project_id"
export CLOUD_ML_REGION="region"
export CLAUDE_CODE_USE_VERTEX="1"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"

# Run analysis (uses config.json for all settings)
# Configure repository, workspace_path, skills, and filters in config.json
python pr-news/end_to_end.py
# (Can be run from any directory - config.json is auto-located)
```

Output shows analysis results with BLOCK/PASS verdicts:

```
[1/15] Analyzing PR #12345: Fix memory leak in cache layer
  Diff size: 46 lines
  ✓ Verdict: PASS

BLOCKED: 0
PASSED: 15
```

Results are exported to `pr_analysis_results.json` with structured review data.

## Configuration

Edit `config.json` to specify your repository and settings:

```json
{
  "repository": "your-org/your-repo",
  "workspace_path": "/path/to/local/clone",
  "skill_paths": [],
  "filter": {
    "labels": ["bug"],
    "days_back": 7
  }
}
```

**Required fields:**
- `repository`: GitHub repository to fetch PRs from (org/repo format)
- `workspace_path`: Local path to repository clone (where Claude can read code)

**Optional fields:**
- `skill_paths`: Domain-specific skill files for specialized guidance (defaults to [])
- `filter.labels`: GitHub labels to filter PRs
- `filter.authors`: PR authors to include (null = all)
- `filter.days_back`: Number of days to look back

## Example: PyTorch torch.compile Review

This tool was originally built for PyTorch Dynamo and Inductor. See `config.json` for an example configuration that reviews PyTorch PRs with domain-specific skills.

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
