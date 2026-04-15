# PyTorch PR Review Filter

Agentic PR review filter for PyTorch torch.compile using AI-assisted critique to detect critical bugs in Dynamo and Inductor code.

## Overview

This tool analyzes PyTorch pull requests and filters them to identify critical bugs in torch.compile components (Dynamo symbolic execution and Inductor code generation). It uses Claude (via Google Vertex AI) with domain-specific skills to provide high-precision bug detection.

**Design Philosophy**: Precision over recall — minimize false positives, default to PASS.

## Features

- **Diff Reduction**: Filters PRs to relevant Dynamo/Inductor changes, caps at ~1k lines
- **Agentic Critique**: AI-powered analysis using fresh agent pattern (isolated API call per PR)
- **Binary Filtering**: Only surfaces BLOCK verdicts (critical issues), discards PASS
- **Skill Integration**: Leverages pytorch-dynamo and pytorch-inductor domain expertise
- **CSV Output**: Plain text front page with blocked PRs and concrete issue explanations
- **Configurable**: YAML-based configuration for all settings

## Installation

```bash
cd /workspaces/pytorch-devcontainers/pytorch-pr-review-filter
pip install -e .
```

## Prerequisites

- Python 3.10+
- Google Cloud Platform account with Vertex AI enabled
- GitHub personal access token (read-only)
- Pre-filtered CSV of PRs (from export_prs.py)

## Configuration

Edit `config.yaml` with your settings:

```yaml
repository: "pytorch/pytorch"
input_csv_path: "filtered_prs.csv"

diff_reduction:
  max_lines: 1000
  priority_dirs:
    - "torch/_dynamo"
    - "torch/_inductor"

model_params:
  temperature: 0.2
  max_tokens: 2000

skill_paths:
  - "/workspaces/pytorch-devcontainers/.claude/skills/pytorch-dynamo.md"
  - "/workspaces/pytorch-devcontainers/.claude/skills/pytorch-inductor.md"
  - "skills/pr_critique.md"

self_check_enabled: true
```

## Usage

### Basic Usage

```bash
# Set environment variables
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Run PR review
python review_prs.py
```

### Command-Line Options

```bash
python review_prs.py --config custom.yaml    # Use custom config
python review_prs.py --dry-run               # Validate without API calls
python review_prs.py --verbose               # Enable detailed logging
python review_prs.py --output custom.csv     # Custom output path
```

## Output

### Stdout Progress

```
[1/10] Analyzing PR #12345: Fix guard generation
  Diff reduced: 1234 → 456 lines
  🚫 Verdict: BLOCK (confidence: HIGH)
  Issue: Guard generation logic fails to account for list mutation...

[2/10] Analyzing PR #12346: Refactor utils
  Diff reduced: 234 → 234 lines
  ✓ Verdict: PASS

==============================================================
PR Review Complete
==============================================================
Total PRs analyzed: 10
BLOCKED: 2
PASSED: 7
SKIPPED: 1
Block rate: 20.0%

Output written to: pr_review_20260415_143000.csv

BLOCKED PRs:
  • #12345 [HIGH] Fix guard generation
    https://github.com/pytorch/pytorch/pull/12345
```

### CSV Output

Only BLOCK verdicts appear in the output CSV:

| pr_number | title | url | verdict | confidence | issue_explanation |
|-----------|-------|-----|---------|------------|-------------------|
| 12345 | Fix guard generation | https://... | BLOCK | HIGH | Guard generation logic in guards.py line 42 fails to account for list mutation... |

## Architecture

### Data Flow

```
export_prs.py → CSV (pre-filtered)
    ↓
pr_filter/diff_reducer.py → Reduced diffs (~1k lines, Dynamo/Inductor only)
    ↓
pr_filter/critique.py → BLOCK/PASS verdicts (fresh agent per PR)
    ↓
pr_filter/generator.py → CSV output (BLOCK verdicts only)
```

### Fresh Agent Pattern

Each PR gets a completely isolated, stateless API call. No shared session or context across PRs.

```python
# CORRECT: Fresh agent per PR
for pr in prs:
    result = critique_pr(pr, reduced_diff, config)  # New API call each time

# WRONG: Session reuse (context bleeding)
session = vertex.start_chat()  # DO NOT DO THIS
for pr in prs:
    session.send_message(pr_diff)
```

## Skills

The tool uses three skill files:

1. **pytorch-dynamo.md** (shared) — Dynamo symbolic execution internals
2. **pytorch-inductor.md** (shared) — Inductor code generation internals  
3. **pr_critique.md** (repo-local) — PR critique criteria and decision contract

Edit `skills/pr_critique.md` to tune critique behavior.

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_diff_reducer.py -v

# With coverage
pytest tests/ --cov=pr_filter --cov-report=html
```

## Troubleshooting

### "Config file not found"
- Ensure `config.yaml` exists in the repository root
- Or use `--config` to specify a custom path

### "Input CSV not found"
- Run `export_prs.py` first to generate the pre-filtered CSV
- Or update `input_csv_path` in config.yaml

### "API authentication failed"
- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account JSON
- Ensure service account has Vertex AI User role

### "All verdicts are PASS"
- This may be correct if PRs don't have critical issues
- Or skills may be too permissive — review `skills/pr_critique.md`
- Or temperature too high — try lowering to 0.1

### "Too many BLOCK verdicts (false positives)"
- Enable `self_check_enabled: true` in config.yaml
- Lower temperature to 0.1 for more conservative verdicts
- Update `skills/pr_critique.md` to add "NOT Critical" examples

## Performance

- **Diff reduction**: <1 second per PR
- **Critique (API call)**: 5-30 seconds per PR (Vertex AI latency)
- **Total for 10 PRs**: ~2-5 minutes (sequential)

**Note**: Sequential processing is acceptable for typical volume (<10 PRs).

## Success Metrics

- **Precision**: ≥90% of BLOCK verdicts contain real critical issues
- **False Positive Rate**: <10%
- **Default Behavior**: PASS unless highly confident of concrete bug

## Project Structure

```
pytorch-pr-review-filter/
├── README.md
├── pyproject.toml
├── config.yaml
├── review_prs.py              # CLI entry point
├── pr_filter/
│   ├── __init__.py
│   ├── models.py              # Data models
│   ├── config.py              # Configuration
│   ├── diff_reducer.py        # Diff filtering
│   ├── critique.py            # AI critique (fresh agent pattern)
│   └── generator.py           # Front page binary filter
├── skills/
│   └── pr_critique.md         # Critique criteria
└── tests/
    ├── test_diff_reducer.py
    ├── test_critique.py
    ├── test_generator.py
    └── test_integration.py
```

## Dependencies

- **pytorch-jira-bot**: GitHub API and Vertex AI Claude integration
- **pyyaml**: Configuration management
- **pandas**: CSV I/O
- **pytest**: Testing framework

## License

See pytorch-jira-bot repository for licensing information.

## Contributing

This tool extends pytorch-jira-bot infrastructure. For questions or contributions, refer to the PyTorch torch.compile team.

## Links

- **Specification**: `/workspaces/pytorch-devcontainers/specs/001-agentic-issue-filter/spec.md`
- **Implementation Plan**: `/workspaces/pytorch-devcontainers/specs/001-agentic-issue-filter/plan.md`
- **Task Breakdown**: `/workspaces/pytorch-devcontainers/specs/001-agentic-issue-filter/tasks.md`
