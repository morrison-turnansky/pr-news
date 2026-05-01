#!/usr/bin/env python3
"""
End-to-end demo: Fetch and analyze PRs from GitHub.

This demonstrates the complete workflow:
1. Load configuration from config.json
2. Fetch PRs from GitHub matching filter criteria
3. Analyze each PR with Claude Code agent
4. Export results to JSON

Configuration is read from config.json (repository, filters, skill paths).

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
from pathlib import Path

from pr_filter.config import load_config
from pr_filter.critique import critique_pr
from pr_filter.data_structs import ReviewResult, Verdict
from pr_filter.filter import diff_filter, fetch_prs
from pr_filter.output import export_json, print_review


def main():
    """Run end-to-end PR analysis demo."""
    # Verify GitHub token
    github_token = os.environ.get("GH_TOKEN")
    if not github_token:
        print("ERROR: GH_TOKEN environment variable required")
        print("\nSet it with: export GH_TOKEN=your_github_token")
        sys.exit(1)

    # Load configuration from JSON
    # All settings (repository, skill_paths, filter criteria) come from config.json
    # Use path relative to this script's location
    script_dir = Path(__file__).parent
    config_path = script_dir / "config.json"
    config = load_config(str(config_path))

    # Use filter configuration from config.json
    # The config already contains filter_config from the JSON file
    filter_criteria = config.filter_config

    # Verify Vertex AI configuration
    try:
        config.verify_vertex_env()
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nEnsure Vertex AI environment variables are set.")
        sys.exit(1)

    # Display configuration
    print("=" * 70)
    print("PR Review Filter - End-to-End Demo")
    print("=" * 70)
    print(f"Repository: {filter_criteria.repo}")
    print(f"Labels: {filter_criteria.labels}")
    created_after_str = filter_criteria.created_after.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Created after: {created_after_str}")

    # Display active boolean filters
    if filter_criteria.is_merged is not None:
        status = "merged only" if filter_criteria.is_merged else "unmerged only"
        print(f"Merge status: {status}")
    if filter_criteria.is_open is not None:
        status = "open only" if filter_criteria.is_open else "closed only"
        print(f"Open status: {status}")
    if filter_criteria.is_draft is not None:
        status = "drafts only" if filter_criteria.is_draft else "non-drafts only"
        print(f"Draft status: {status}")

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

    # Step 1.5: Apply diff-based filtering
    print("Step 1.5: Applying diff-based filtering...")
    diff_cfg = config.diff_filter_config
    active_filters = []
    if diff_cfg.max_lines_changed is not None:
        active_filters.append(f"max_lines: {diff_cfg.max_lines_changed}")
    if diff_cfg.max_files_changed is not None:
        active_filters.append(f"max_files: {diff_cfg.max_files_changed}")
    if diff_cfg.only_test_files is not None:
        status = "only test files" if diff_cfg.only_test_files else "at least one non-test file"
        active_filters.append(f"files: {status}")

    if active_filters:
        print(f"  Active diff filters: {', '.join(active_filters)}")
        original_count = len(prs)
        prs = diff_filter(
            prs,
            max_lines_changed=diff_cfg.max_lines_changed,
            max_files_changed=diff_cfg.max_files_changed,
            only_test_files=diff_cfg.only_test_files,
        )
        filtered_count = original_count - len(prs)
        print(f"  Filtered out {filtered_count} PR(s), {len(prs)} remaining")
    else:
        print("  No diff filters active, skipping")

    print()

    if len(prs) == 0:
        print("No PRs found matching filter criteria.")
        print("Tip: Adjust the date range or diff filters if needed.")
        sys.exit(0)

    # Step 2: Analyze PRs
    print("Step 2: Analyzing PRs with Claude Code agent...")
    print()

    all_results: list[ReviewResult] = []
    blocked_prs: list[ReviewResult] = []

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
            print(f"   Summary: {result.summary}")
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
