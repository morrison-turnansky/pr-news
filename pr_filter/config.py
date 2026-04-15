"""Configuration models for PR review filter."""

from dataclasses import dataclass, field


@dataclass
class DiffReductionConfig:
    """Diff reduction settings."""
    max_lines: int = 1000
    priority_dirs: list[str] = field(default_factory=lambda: [
        "torch/_dynamo",
        "torch/_inductor"
    ])


@dataclass
class ModelParams:
    """Claude model parameters."""
    temperature: float = 0.2  # Lower = more conservative
    max_tokens: int = 2000


@dataclass
class PRReviewConfig:
    """Main configuration for PR review pipeline."""
    repository: str  # e.g., "pytorch/pytorch"
    input_csv_path: str  # Path to pre-filtered CSV

    diff_reduction: DiffReductionConfig = field(default_factory=DiffReductionConfig)
    model_params: ModelParams = field(default_factory=ModelParams)

    skill_paths: list[str] = field(default_factory=lambda: [
        "/workspaces/pytorch-devcontainers/.claude/skills/pytorch-dynamo.md",
        "/workspaces/pytorch-devcontainers/.claude/skills/pytorch-inductor.md",
        "skills/pr_critique.md"  # Repo-local skill
    ])

    self_check_enabled: bool = True

    # Optional filters (applied during CSV load)
    date_range_days: int = 7
    exclude_labels: list[str] = field(default_factory=list)
    min_diff_lines: int = 10


def load_config(config_path: str) -> PRReviewConfig:
    """Load configuration from YAML file."""
    import yaml

    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)

    # Handle nested structures
    diff_reduction_dict = config_dict.get('diff_reduction', {})
    model_params_dict = config_dict.get('model_params', {})

    diff_reduction = DiffReductionConfig(
        max_lines=diff_reduction_dict.get('max_lines', 1000),
        priority_dirs=diff_reduction_dict.get('priority_dirs', [
            "torch/_dynamo",
            "torch/_inductor"
        ])
    )

    model_params = ModelParams(
        temperature=model_params_dict.get('temperature', 0.2),
        max_tokens=model_params_dict.get('max_tokens', 2000)
    )

    return PRReviewConfig(
        repository=config_dict['repository'],
        input_csv_path=config_dict['input_csv_path'],
        diff_reduction=diff_reduction,
        model_params=model_params,
        skill_paths=config_dict.get('skill_paths', [
            "/workspaces/pytorch-devcontainers/.claude/skills/pytorch-dynamo.md",
            "/workspaces/pytorch-devcontainers/.claude/skills/pytorch-inductor.md",
            "skills/pr_critique.md"
        ]),
        self_check_enabled=config_dict.get('self_check_enabled', True),
        date_range_days=config_dict.get('date_range_days', 7),
        exclude_labels=config_dict.get('exclude_labels', []),
        min_diff_lines=config_dict.get('min_diff_lines', 10)
    )
