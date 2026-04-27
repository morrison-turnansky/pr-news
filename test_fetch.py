#!/usr/bin/env python3
"""Test PR fetching"""

import os
from datetime import datetime, timedelta

from pytorch_jira_bot.sync.github import GitHubClient

github_token = os.environ.get("GH_TOKEN")
if not github_token:
    print("ERROR: GH_TOKEN required")
    exit(1)

print("Testing PR fetch from pytorch/pytorch...")

with GitHubClient(token=github_token, repos=["pytorch/pytorch"]) as client:
    created_after = datetime.now() - timedelta(days=7)
    print(f"Looking for PRs created after: {created_after}")

    pr_reviews = client.get_prs_by_filter(
        authors=None,
        labels=None,
        created_after=created_after,
        created_before=None,
    )

    print(f"Found {len(pr_reviews)} PRs")

    for pr_review in pr_reviews[:5]:
        pr = pr_review.pr
        print(f"  - PR #{pr.number}: {pr.title[:60]}...")
