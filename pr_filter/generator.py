"""Front page generator with binary filtering (BLOCK only)."""

import csv
from datetime import datetime
from pr_filter.models import CritiquedPR, FrontPage, SummaryStats


def generate_front_page(critiqued_prs: list[CritiquedPR]) -> FrontPage:
    """
    Generate front page with binary filtering.

    Only PRs with BLOCK verdict are included.
    PASS verdicts are discarded (binary inclusion).

    Args:
        critiqued_prs: List of CritiquedPR objects

    Returns:
        FrontPage with only BLOCK verdicts
    """
    # Binary filter: include only BLOCK verdicts
    blocked_prs = [pr for pr in critiqued_prs if pr.verdict == "BLOCK"]

    # Calculate summary stats
    blocked_count = len(blocked_prs)
    passed_count = len([pr for pr in critiqued_prs if pr.verdict == "PASS"])

    summary_stats = SummaryStats(
        blocked_count=blocked_count,
        passed_count=passed_count
    )

    # Create FrontPage
    front_page = FrontPage(
        generated_at=datetime.now(),
        blocked_prs=blocked_prs,
        summary_stats=summary_stats
    )

    return front_page


def export_csv(front_page: FrontPage, output_path: str) -> None:
    """
    Export front page to CSV format.

    Args:
        front_page: FrontPage to export
        output_path: Path to write CSV file
    """
    # Define CSV columns
    fieldnames = [
        'pr_number',
        'title',
        'url',
        'verdict',
        'confidence',
        'issue_explanation'
    ]

    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header
        writer.writeheader()

        # Write rows (only BLOCK verdicts)
        for pr in front_page.blocked_prs:
            writer.writerow({
                'pr_number': pr.pr_number,
                'title': pr.title,
                'url': pr.url,
                'verdict': pr.verdict,
                'confidence': pr.confidence or '',
                'issue_explanation': pr.issue_explanation
            })


def generate_timestamp_filename() -> str:
    """
    Generate timestamped filename for CSV output.

    Returns:
        Filename in format: pr_review_YYYYMMDD_HHMMSS.csv
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"pr_review_{timestamp}.csv"
