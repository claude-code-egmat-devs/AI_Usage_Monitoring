#!/usr/bin/env python3
"""
Daily Report Generator v2
Aggregates AI usage across all apps using adapters for different log formats.
Backward compatible with existing JSONL apps, adds support for new formats.

Deploy to: /home/.ai_monitoring/services/daily_report_v2.py

Run via cron at 11:30 PM IST (6:00 PM UTC):
    0 18 * * * /usr/bin/python3 /home/.ai_monitoring/services/daily_report_v2.py

Usage:
    python daily_report_v2.py              # Generate and send report
    python daily_report_v2.py --preview    # Preview without sending
    python daily_report_v2.py --date 2025-01-14  # Report for specific date
"""
import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any, List, Optional

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib'))

try:
    from log_adapters import get_adapter, ADAPTER_TYPES
except ImportError:
    # Fallback if log_adapters not available
    print("Warning: log_adapters module not found, falling back to basic JSONL reading")
    get_adapter = None

# Try to import teams notifier
try:
    from teams_notifier import send_daily_report, send_alert, load_settings
except ImportError:
    # Alternative path for VPS
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    try:
        from lib.teams_notifier import send_daily_report, send_alert, load_settings
    except ImportError:
        print("Error: teams_notifier module not found")
        sys.exit(1)


def read_jsonl_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Fallback function to read JSONL file (for backward compatibility).
    Used when log_adapters module is not available.
    """
    entries = []
    if not os.path.exists(file_path):
        return entries

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return entries


def filter_entries_by_date(
    entries: List[Dict[str, Any]],
    target_date: datetime
) -> List[Dict[str, Any]]:
    """Filter log entries for a specific date."""
    target_str = target_date.strftime('%Y-%m-%d')
    return [
        e for e in entries
        if e.get('timestamp', '').startswith(target_str)
    ]


def filter_entries_by_month(
    entries: List[Dict[str, Any]],
    year: int,
    month: int
) -> List[Dict[str, Any]]:
    """Filter log entries for a specific month."""
    month_prefix = f"{year}-{month:02d}"
    return [
        e for e in entries
        if e.get('timestamp', '').startswith(month_prefix)
    ]


def aggregate_usage(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate usage statistics from log entries."""
    stats = {
        'requests': 0,
        'total_tokens': 0,
        'total_cost': 0.0,
        'input_tokens': 0,
        'output_tokens': 0,
        'cache_creation_tokens': 0,
        'cache_read_tokens': 0,
        'thinking_tokens': 0,
        'errors': 0,
        'models': defaultdict(lambda: {'calls': 0, 'cost': 0.0}),
        'purposes': defaultdict(int)
    }

    for entry in entries:
        stats['requests'] += 1

        # Handle both nested tokens dict and flat structure
        tokens = entry.get('tokens', {})
        if isinstance(tokens, dict):
            stats['input_tokens'] += tokens.get('input', 0) or 0
            stats['output_tokens'] += tokens.get('output', 0) or 0
            stats['cache_creation_tokens'] += tokens.get('cache_creation', 0) or 0
            stats['cache_read_tokens'] += tokens.get('cache_read', 0) or 0
            stats['thinking_tokens'] += tokens.get('thinking', 0) or 0
            stats['total_tokens'] += (
                (tokens.get('input', 0) or 0) +
                (tokens.get('output', 0) or 0) +
                (tokens.get('cache_creation', 0) or 0)
            )
        else:
            # Flat structure fallback
            stats['input_tokens'] += entry.get('input_tokens', 0) or 0
            stats['output_tokens'] += entry.get('output_tokens', 0) or 0
            stats['total_tokens'] += (
                (entry.get('input_tokens', 0) or 0) +
                (entry.get('output_tokens', 0) or 0)
            )

        cost = entry.get('cost_usd', 0) or 0
        stats['total_cost'] += cost

        if not entry.get('success', True):
            stats['errors'] += 1

        model = entry.get('model', 'unknown')
        stats['models'][model]['calls'] += 1
        stats['models'][model]['cost'] += cost

        purpose = entry.get('purpose', 'unknown')
        stats['purposes'][purpose] += 1

    return stats


def get_entries_for_app(
    app_name: str,
    app_config: Dict[str, Any],
    target_date: datetime
) -> tuple:
    """
    Get entries for an app for today and the month.

    Returns:
        Tuple of (today_entries, month_entries)
    """
    # Determine the adapter type
    adapter_type = app_config.get('adapter_type', 'jsonl')

    # If we have the adapters module, use it
    if get_adapter is not None:
        try:
            adapter = get_adapter(app_name, app_config)

            # Get today's entries
            today_entries = adapter.get_entries_for_date(target_date)

            # Get month's entries
            month_entries = adapter.get_entries_for_month(
                target_date.year,
                target_date.month
            )

            return today_entries, month_entries
        except Exception as e:
            print(f"Error using adapter for {app_name}: {e}")
            # Fall back to direct JSONL reading if possible
            pass

    # Fallback: direct JSONL reading for backward compatibility
    log_file = app_config.get('log_file')
    if not log_file:
        return [], []

    all_entries = read_jsonl_file(log_file)
    today_entries = filter_entries_by_date(all_entries, target_date)
    month_entries = filter_entries_by_month(all_entries, target_date.year, target_date.month)

    return today_entries, month_entries


def generate_report(target_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Generate daily report data."""
    if target_date is None:
        target_date = datetime.now()

    settings = load_settings()
    apps_config = settings.get('apps', {})

    report = {
        'date': target_date.strftime('%Y-%m-%d'),
        'apps': {},
        'models': defaultdict(lambda: {'calls': 0, 'cost': 0.0}),
        'today_cost': 0.0,
        'month_cost': 0.0,
        'budget': settings.get('thresholds', {}).get('monthly_budget_usd', 100),
        'total_requests': 0,
        'total_errors': 0,
        'adapters_used': []
    }

    # Process each app
    for app_name, app_config in apps_config.items():
        adapter_type = app_config.get('adapter_type', 'jsonl')
        report['adapters_used'].append(f"{app_name}:{adapter_type}")

        try:
            today_entries, month_entries = get_entries_for_app(
                app_name, app_config, target_date
            )

            today_stats = aggregate_usage(today_entries)
            month_stats = aggregate_usage(month_entries)

            # Add to report
            report['apps'][app_name] = {
                'requests': today_stats['requests'],
                'total_tokens': today_stats['total_tokens'],
                'total_cost': today_stats['total_cost'],
                'errors': today_stats['errors'],
                'month_cost': month_stats['total_cost'],
                'adapter': adapter_type,
                'description': app_config.get('description', '')
            }

            report['today_cost'] += today_stats['total_cost']
            report['month_cost'] += month_stats['total_cost']
            report['total_requests'] += today_stats['requests']
            report['total_errors'] += today_stats['errors']

            # Aggregate models
            for model, model_stats in today_stats['models'].items():
                report['models'][model]['calls'] += model_stats['calls']
                report['models'][model]['cost'] += model_stats['cost']

        except Exception as e:
            print(f"Error processing {app_name}: {e}")
            report['apps'][app_name] = {
                'requests': 0,
                'total_tokens': 0,
                'total_cost': 0,
                'errors': 0,
                'month_cost': 0,
                'adapter': adapter_type,
                'error': str(e)
            }

    # Convert defaultdict to regular dict
    report['models'] = dict(report['models'])

    return report


def check_thresholds(report: Dict[str, Any]) -> None:
    """Check if any thresholds are exceeded and send alerts."""
    settings = load_settings()
    thresholds = settings.get('thresholds', {})

    today_cost = report.get('today_cost', 0)
    month_cost = report.get('month_cost', 0)
    budget = report.get('budget', 100)

    # Check daily critical
    daily_critical = thresholds.get('daily_critical_usd', 10)
    if today_cost >= daily_critical:
        send_alert('daily_critical', {
            'cost': today_cost,
            'threshold': daily_critical
        })
    # Check daily warning
    elif today_cost >= thresholds.get('daily_warning_usd', 5):
        send_alert('daily_warning', {
            'cost': today_cost,
            'threshold': thresholds.get('daily_warning_usd', 5)
        })

    # Check budget warning
    budget_alert_percent = thresholds.get('budget_alert_percent', 80)
    if budget > 0:
        usage_percent = (month_cost / budget) * 100
        if usage_percent >= budget_alert_percent:
            send_alert('budget_warning', {
                'spent': month_cost,
                'budget': budget,
                'percent': usage_percent
            })


def print_preview(report: Dict[str, Any]) -> None:
    """Print a preview of the report to console."""
    print("\n" + "=" * 60)
    print(f"AI USAGE DAILY REPORT - {report['date']}")
    print("=" * 60)

    print(f"\n{'APP':<25} {'REQUESTS':<10} {'TOKENS':<12} {'TODAY $':<10} {'MONTH $':<10}")
    print("-" * 67)

    for app_name, app_data in report['apps'].items():
        adapter = app_data.get('adapter', 'jsonl')
        requests = app_data.get('requests', 0)
        tokens = app_data.get('total_tokens', 0)
        today_cost = app_data.get('total_cost', 0)
        month_cost = app_data.get('month_cost', 0)

        display_name = app_name[:23] + '..' if len(app_name) > 25 else app_name
        print(f"{display_name:<25} {requests:<10} {tokens:<12,} ${today_cost:<9.2f} ${month_cost:<9.2f}")

        if 'error' in app_data:
            print(f"  -> ERROR: {app_data['error']}")

    print("-" * 67)
    print(f"{'TOTAL':<25} {report['total_requests']:<10} {'-':<12} ${report['today_cost']:<9.2f} ${report['month_cost']:<9.2f}")

    print(f"\n{'MODEL':<30} {'CALLS':<10} {'COST $':<10}")
    print("-" * 50)
    for model, stats in report['models'].items():
        display_model = model[:28] + '..' if len(model) > 30 else model
        print(f"{display_model:<30} {stats['calls']:<10} ${stats['cost']:<9.2f}")

    print(f"\nBudget: ${report['month_cost']:.2f} / ${report['budget']:.2f} ({report['month_cost']/report['budget']*100:.0f}%)" if report['budget'] > 0 else "")
    print(f"Errors: {report['total_errors']}")
    print(f"Adapters: {', '.join(report.get('adapters_used', []))}")
    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='AI Usage Daily Report Generator v2')
    parser.add_argument('--preview', action='store_true', help='Preview report without sending')
    parser.add_argument('--date', type=str, help='Generate report for specific date (YYYY-MM-DD)')
    parser.add_argument('--json', action='store_true', help='Output raw JSON')
    args = parser.parse_args()

    # Parse target date
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        target_date = datetime.now()

    print(f"Generating daily report for {target_date.strftime('%Y-%m-%d')}...")

    # Generate report
    report = generate_report(target_date)

    # Output based on mode
    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return report

    print(f"Report generated:")
    print(f"  - Date: {report['date']}")
    print(f"  - Apps: {len(report['apps'])}")
    print(f"  - Today's cost: ${report['today_cost']:.2f}")
    print(f"  - Month-to-date: ${report['month_cost']:.2f}")

    if args.preview:
        print_preview(report)
        print("(Preview mode - report not sent)")
        return report

    # Check thresholds first (sends alerts if needed)
    check_thresholds(report)

    # Send daily report
    success = send_daily_report(report)

    if success:
        print("Daily report sent successfully!")
    else:
        print("Failed to send daily report")

    return report


if __name__ == "__main__":
    main()
