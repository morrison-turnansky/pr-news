#!/usr/bin/env python3
"""Quick test with a single small PR."""

import os
import sys

from pr_filter.config import load_config
from pr_filter.critique import critique_pr
from pr_filter.filter import fetch_prs
from pr_filter.output import print_review

# Verify env
github_token = os.environ.get("GH_TOKEN")
if not github_token:
    print("ERROR: GH_TOKEN required")
    sys.exit(1)

# Load config
config = load_config("config.json")

try:
    config.verify_vertex_env()
except ValueError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Use filter from config but limit to 1 day to get smaller PRs
filter_criteria = config.filter_config

print(f"Fetching PRs from {filter_criteria.repo}...")
print(f"Labels: {filter_criteria.labels}")

# Fetch PRs
prs = fetch_prs(github_token=github_token, filter_criteria=filter_criteria)

if not prs:
    print("No PRs found")
    sys.exit(0)

# Sort by diff size, pick smallest
prs.sort(key=lambda p: p.diff_lines)
pr = prs[0]

print(f"\nTesting with smallest PR: #{pr.pr_number}")
print(f"Title: {pr.title}")
print(f"Diff lines: {pr.diff_lines}")
print()

# Analyze
try:
    result = critique_pr(pr, config)
    print_review(result, show_all_comments=True)
    print("\n✅ SUCCESS - Got a result!")
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
