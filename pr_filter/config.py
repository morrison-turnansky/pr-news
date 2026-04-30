"""Configuration management for PR review filter."""

import json
from datetime import datetime, timedelta

from pr_filter.data_structs import PRFilter, PRReviewConfig


def load_config(config_path: str) -> PRReviewConfig:
    """Load configuration from JSON file.

    The filter section supports:
    - days_back: Number of days to look back (converted to created_after)
    - created_after: ISO format date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    - created_before: ISO format date string

    If days_back is set, it takes precedence over created_after.
    """
    with open(config_path) as f:
        config_dict = json.load(f)

    # Parse filter configuration
    filter_dict = config_dict.get("filter", {})

    # Handle date filtering
    created_after = None
    if filter_dict.get("days_back"):
        # Convert days_back to created_after
        days_back = filter_dict["days_back"]
        created_after = datetime.now() - timedelta(days=days_back)
    elif filter_dict.get("created_after"):
        # Use explicit created_after date
        created_after = datetime.fromisoformat(filter_dict["created_after"])

    created_before = None
    if filter_dict.get("created_before"):
        created_before = datetime.fromisoformat(filter_dict["created_before"])

    filter_config = PRFilter(
        repo=config_dict.get("repository", "pytorch/pytorch"),
        authors=filter_dict.get("authors"),
        labels=filter_dict.get("labels"),
        created_after=created_after,
        created_before=created_before,
        is_merged=filter_dict.get("is_merged"),
        is_open=filter_dict.get("is_open"),
        is_draft=filter_dict.get("is_draft"),
    )

    # Get skill_paths if provided (defaults to [] if not present or None)
    skill_paths = config_dict.get("skill_paths") or []

    return PRReviewConfig(
        repository=config_dict["repository"],
        workspace_path=config_dict["workspace_path"],
        filter_config=filter_config,
        skill_paths=skill_paths,
    )
