#!/usr/bin/env python3
"""
End-to-end demo: Fetch and analyze PyTorch PRs with dynamo label.

This demonstrates the complete workflow:
1. Load configuration
2. Fetch PRs from GitHub
3. Analyze each PR with Claude Code agent
4. Export results to JSON

Usage:
    python end_to_end.py

Required environment variables:
    - GH_TOKEN: GitHub personal access token
    - ANTHROPIC_VERTEX_PROJECT_ID: Vertex AI project ID
    - CLOUD_ML_REGION: Vertex AI region (e.g., us-east5)
    - CLAUDE_CODE_USE_VERTEX: Set to "1"
    - GOOGLE_APPLICATION_CREDENTIALS: Path to gcloud credentials
"""

import os
import sys
from datetime import datetime, timedelta

from pr_filter.config import PRReviewConfig
from pr_filter.critique import critique_pr
from pr_filter.data_structs import PRFilter, Verdict
from pr_filter.filter import fetch_prs
from pr_filter.output import export_json, print_review


def main():
    """Run end-to-end PR analysis demo."""
    # Verify GitHub token
    github_token = os.environ.get("GH_TOKEN")
    if not github_token:
        print("ERROR: GH_TOKEN environment variable required")
        print("\nSet it with: export GH_TOKEN=your_github_token")
        sys.exit(1)

    # Configure analysis
    now = datetime.now()
    two_days_ago = now - timedelta(days=1)

    filter_criteria = PRFilter(
        repo="pytorch/pytorch",
        labels=["module: dynamo"],
        created_after=two_days_ago,
        authors=None,
    )

    skills_base = "/workspaces/pytorch-devcontainers/.claude/skills"
    config = PRReviewConfig(
        repository="pytorch/pytorch",
        skill_paths=[
            f"{skills_base}/pytorch-dynamo/SKILL.md",
            f"{skills_base}/pytorch-inductor/SKILL.md",
        ],
    )

    # Verify Vertex AI configuration
    try:
        config.verify_vertex_env()
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nEnsure Vertex AI environment variables are set.")
        sys.exit(1)

    # Display configuration
    print("=" * 70)
    print("PyTorch PR Review - End-to-End Demo")
    print("=" * 70)
    print(f"Repository: {filter_criteria.repo}")
    print(f"Labels: {filter_criteria.labels}")
    created_after_str = filter_criteria.created_after.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Created after: {created_after_str}")
    print()

    # Step 1: Fetch PRs
    print("Step 1: Fetching PRs from GitHub...")
    try:
        prs = fetch_prs(github_token=github_token, filter_criteria=filter_criteria)
    except Exception as e:
        print(f"ERROR: Failed to fetch PRs: {e}")
        sys.exit(2)

    print(f"✅ Fetched {len(prs)} PR(s)")
    print()

    if len(prs) == 0:
        print("No PRs found matching filter criteria.")
        print("Tip: Adjust the date range if needed.")
        sys.exit(0)

    # Step 2: Analyze PRs
    print("Step 2: Analyzing PRs with Claude Code agent...")
    print()

    all_results = []
    blocked_prs = []

    for i, pr in enumerate(prs, 1):
        print(f"[{i}/{len(prs)}] PR #{pr.pr_number}: {pr.title}")

        # Skip PRs with no diff
        if not pr.diff or len(pr.diff.strip()) == 0:
            print("  ⚠️  No diff available (skipping)")
            print()
            continue

        print(f"  Diff size: {pr.diff_lines} lines")
        print()

        # Analyze PR
        try:
            result = critique_pr(pr, config)
            all_results.append(result)

            # Display review
            print_review(result, show_all_comments=True)

            # Collect blocked PRs
            if result.verdict == Verdict.BLOCK:
                blocked_prs.append(result)

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            print(f"  Skipping PR #{pr.pr_number}")
            print()
            continue
        break

    # Step 3: Display summary
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total PRs analyzed: {len(all_results)}")
    print(f"BLOCKED: {len(blocked_prs)}")
    print(f"PASSED: {len(all_results) - len(blocked_prs)}")
    print()

    if len(blocked_prs) == 0:
        print("✅ No critical bugs found!")
    else:
        print("🚫 BLOCKED PRs (Critical Bugs Found):")
        print()
        for i, result in enumerate(blocked_prs, 1):
            print(f"{i}. PR #{result.pr_number} - {result.title}")
            print(f"   Author: {result.author}")
            print(f"   URL: {result.url}")
            print(
                f"   Issues: {result.summary.total_issues} "
                f"(Critical: {result.summary.critical}, Major: {result.summary.major})"
            )
            print(f"   {result.summary.explanation}")
            print()

    # Step 4: Export results
    if all_results:
        output_file = "pr_analysis_results.json"
        export_json(all_results, output_file)
        print(f"📄 Results exported to: {output_file}")
        print()

    print("=" * 70)
    print("✅ Analysis complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
