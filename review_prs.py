"""
CLI entry point for PR review filter.

Usage:
    python review_prs.py                    # Use default config.yaml
    python review_prs.py --config custom.yaml
    python review_prs.py --dry-run          # Validate without API calls
    python review_prs.py --verbose          # Enable detailed logging
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from pr_filter.config import load_config
from pr_filter.models import PullRequest
from pr_filter.diff_reducer import reduce_diff
from pr_filter.critique import critique_pr
from pr_filter.generator import generate_front_page, export_csv, generate_timestamp_filename


def main():
    """Main entry point for PR review CLI."""
    # Parse command-line arguments
    args = parse_args()

    # Load configuration
    config_path = args.config
    if not Path(config_path).exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    if args.verbose:
        print(f"Loading config from {config_path}")

    config = load_config(config_path)

    # Read input CSV
    if not Path(config.input_csv_path).exists():
        print(f"ERROR: Input CSV not found: {config.input_csv_path}")
        sys.exit(2)

    if args.verbose:
        print(f"Reading input from {config.input_csv_path}")

    prs = load_prs_from_csv(config.input_csv_path)

    if len(prs) == 0:
        print("WARNING: No PRs found in input CSV")
        sys.exit(0)

    print(f"Loaded {len(prs)} PRs from {config.input_csv_path}")
    print()

    # Dry-run mode
    if args.dry_run:
        print("DRY RUN MODE - No API calls will be made")
        print(f"Would analyze {len(prs)} PRs")
        print(f"Diff reduction: max {config.diff_reduction.max_lines} lines, dirs: {', '.join(config.diff_reduction.priority_dirs)}")
        print(f"Model params: temp={config.model_params.temperature}, max_tokens={config.model_params.max_tokens}")
        print(f"Skills: {len(config.skill_paths)} files")
        print(f"Self-check: {'enabled' if config.self_check_enabled else 'disabled'}")
        sys.exit(0)

    # Main pipeline loop
    critiqued_prs = []
    skipped_count = 0

    for i, pr in enumerate(prs, 1):
        print(f"[{i}/{len(prs)}] Analyzing PR #{pr.pr_number}: {pr.title}")

        try:
            # Step 1: Reduce diff
            reduced_diff = reduce_diff(pr, config)

            if not reduced_diff or len(reduced_diff.strip()) == 0:
                print(f"  ⚠️  No relevant changes after diff reduction (skipping)")
                skipped_count += 1
                continue

            original_lines = pr.diff_lines
            reduced_lines = len(reduced_diff.splitlines())
            print(f"  Diff reduced: {original_lines} → {reduced_lines} lines")

            # Step 2: Critique PR (fresh agent per PR)
            result = critique_pr(pr, reduced_diff, config)

            # Step 3: Log verdict
            verdict_emoji = "🚫" if result.verdict == "BLOCK" else "✓"
            confidence_text = f" (confidence: {result.confidence})" if result.confidence else ""
            print(f"  {verdict_emoji} Verdict: {result.verdict}{confidence_text}")

            if result.verdict == "BLOCK":
                # Show brief excerpt of explanation
                explanation_preview = result.issue_explanation[:100] + "..." if len(result.issue_explanation) > 100 else result.issue_explanation
                print(f"  Issue: {explanation_preview}")

            critiqued_prs.append(result)
            print()

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            print(f"  Skipping PR #{pr.pr_number}")
            skipped_count += 1
            print()

    # Generate front page
    print("=" * 60)
    print("Generating front page...")
    front_page = generate_front_page(critiqued_prs)

    # Optional: sort by confidence
    front_page.sort_by_confidence()

    # Export to CSV
    output_filename = args.output if args.output else generate_timestamp_filename()
    export_csv(front_page, output_filename)

    # Print summary
    print()
    print("=" * 60)
    print("PR Review Complete")
    print("=" * 60)
    print(f"Total PRs analyzed: {front_page.summary_stats.total_analyzed}")
    print(f"BLOCKED: {front_page.summary_stats.blocked_count}")
    print(f"PASSED: {front_page.summary_stats.passed_count}")
    print(f"SKIPPED: {skipped_count}")
    print(f"Block rate: {front_page.summary_stats.block_rate:.1f}%")
    print()
    print(f"Output written to: {output_filename}")
    print()

    if front_page.summary_stats.blocked_count > 0:
        print("BLOCKED PRs:")
        for pr in front_page.blocked_prs:
            confidence_badge = f"[{pr.confidence}]" if pr.confidence else ""
            print(f"  • #{pr.pr_number} {confidence_badge} {pr.title}")
            print(f"    {pr.url}")
        print()

    print("✅ Done!")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Agentic PR review filter for PyTorch torch.compile",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--input',
        help='Override input CSV path from config'
    )

    parser.add_argument(
        '--output',
        help='Override output CSV path (default: auto-generated with timestamp)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate config and input without making API calls'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable detailed debug logging'
    )

    return parser.parse_args()


def load_prs_from_csv(csv_path: str) -> list[PullRequest]:
    """
    Load PRs from input CSV file.

    Args:
        csv_path: Path to CSV file

    Returns:
        List of PullRequest objects
    """
    prs = []

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                pr = PullRequest(
                    pr_number=int(row['pr_number']),
                    title=row['title'],
                    url=row['url'],
                    files_changed=row.get('files_changed', '').split(',') if row.get('files_changed') else [],
                    diff=row.get('diff', ''),  # May need to fetch from GitHub API in full implementation
                    created_at=datetime.now(),  # Placeholder
                    updated_at=datetime.now(),  # Placeholder
                    author=row.get('author', 'unknown')
                )
                prs.append(pr)
            except (KeyError, ValueError) as e:
                print(f"WARNING: Skipping invalid row: {e}")
                continue

    return prs


if __name__ == "__main__":
    main()
