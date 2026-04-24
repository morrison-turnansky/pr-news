"""Configuration management for PR review filter."""

from datetime import datetime

import yaml

from pr_filter.data_structs import PRFilter, PRReviewConfig


def load_config(config_path: str) -> PRReviewConfig:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)

    # Parse filter configuration
    filter_dict = config_dict.get("filter", {})
    filter_config = PRFilter(
        repo=config_dict.get("repository", "pytorch/pytorch"),
        authors=filter_dict.get("authors"),
        labels=filter_dict.get("labels"),
        created_after=(
            datetime.fromisoformat(filter_dict["created_after"])
            if filter_dict.get("created_after")
            else None
        ),
        created_before=(
            datetime.fromisoformat(filter_dict["created_before"])
            if filter_dict.get("created_before")
            else None
        ),
    )

    return PRReviewConfig(
        repository=config_dict["repository"],
        filter_config=filter_config,
        skill_paths=config_dict.get(
            "skill_paths",
            [
                "/workspaces/pytorch-devcontainers/.claude/skills/pytorch-dynamo/SKILL.md",
                "/workspaces/pytorch-devcontainers/.claude/skills/pytorch-inductor/SKILL.md",
            ],
        ),
    )
