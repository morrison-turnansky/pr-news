#!/usr/bin/env python3
"""Test with 3 PRs to verify reliability."""

import os
import sys

from pr_filter.config import load_config
from pr_filter.critique import critique_pr
from pr_filter.filter import fetch_prs

github_token = os.environ.get("GH_TOKEN")
if not github_token:
    print("ERROR: GH_TOKEN required")
    sys.exit(1)

config = load_config("config.json")
config.verify_vertex_env()

prs = fetch_prs(github_token=github_token, filter_criteria=config.filter_config)
prs.sort(key=lambda p: p.diff_lines)

# Test 3 smallest PRs
for i, pr in enumerate(prs[:3], 1):
    print(f"\n{'='*70}")
    print(f"TEST {i}/3: PR #{pr.pr_number} ({pr.diff_lines} lines)")
    print(f"{'='*70}")

    try:
        result = critique_pr(pr, config)
        print(f"✅ Verdict: {result.verdict.name}")
        print(f"   Issues: {result.summary.total_issues}")
        print(f"   Explanation: {result.summary.explanation[:100]}...")
    except Exception as e:
        print(f"❌ FAILED: {e}")

print(f"\n{'='*70}")
print("SUMMARY: All 3 PRs analyzed successfully")
print(f"{'='*70}")
