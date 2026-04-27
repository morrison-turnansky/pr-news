#!/usr/bin/env python3
"""Test with a larger PR (the cached sourcelines one)."""

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

# Fetch PRs
print(f"Fetching PRs from {config.filter_config.repo}...")
prs = fetch_prs(github_token=github_token, filter_criteria=config.filter_config)

if not prs:
    print("No PRs found")
    sys.exit(0)

# Find PR #181601 (the cached getsourcelines one)
pr = None
for p in prs:
    if p.pr_number == 181601:
        pr = p
        break

if not pr:
    print("PR #181601 not found in results")
    sys.exit(0)

print(f"\nTesting with PR: #{pr.pr_number}")
print(f"Title: {pr.title}")
print(f"Diff lines: {pr.diff_lines}")
print()

# Analyze
try:
    result = critique_pr(pr, config)
    print_review(result, show_all_comments=True)
    print(f"\n✅ SUCCESS - Verdict: {result.verdict} (0=BLOCK, 1=PASS)")
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
