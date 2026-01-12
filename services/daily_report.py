#!/usr/bin/env python3
"""
Daily Report Generator
Aggregates AI usage across all apps and sends summary to Teams
Run via cron at 11:30 PM IST (6:00 PM UTC)
"""
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib'))

from teams_notifier import send_daily_report, send_alert, load_settings


def read_log_file(file_path):
    """Read and parse a JSONL log file"""
    entries = []
    if not os.path.exists(file_path):
        return entries

    try:
        with open(file_path, 'r') as f:
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


def filter_entries_by_date(entries, target_date):
    """Filter log entries for a specific date"""
    target_str = target_date.strftime('%Y-%m-%d')
    return [
        e for e in entries
        if e.get('timestamp', '').startswith(target_str)
    ]


def filter_entries_by_month(entries, year, month):
    """Filter log entries for a specific month"""
    month_prefix = f"{year}-{month:02d}"
    return [
        e for e in entries
        if e.get('timestamp', '').startswith(month_prefix)
    ]


def aggregate_usage(entries):
    """Aggregate usage statistics from log entries"""
    stats = {
        'requests': 0,
        'total_tokens': 0,
        'total_cost': 0.0,
        'input_tokens': 0,
        'output_tokens': 0,
        'cache_creation_tokens': 0,
        'cache_read_tokens': 0,
        'errors': 0,
        'models': defaultdict(lambda: {'calls': 0, 'cost': 0.0}),
        'purposes': defaultdict(int)
    }

    for entry in entries:
        stats['requests'] += 1

        tokens = entry.get('tokens', {})
        stats['input_tokens'] += tokens.get('input', 0)
        stats['output_tokens'] += tokens.get('output', 0)
        stats['cache_creation_tokens'] += tokens.get('cache_creation', 0)
        stats['cache_read_tokens'] += tokens.get('cache_read', 0)
        stats['total_tokens'] += (
            tokens.get('input', 0) +
            tokens.get('output', 0) +
            tokens.get('cache_creation', 0)
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


def generate_report(target_date=None):
    """Generate daily report data"""
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
        'total_errors': 0
    }

    # Process each app
    for app_name, app_config in apps_config.items():
        log_file = app_config.get('log_file')
        if not log_file:
            continue

        # Read all entries
        all_entries = read_log_file(log_file)

        # Filter for today
        today_entries = filter_entries_by_date(all_entries, target_date)
        today_stats = aggregate_usage(today_entries)

        # Filter for month
        month_entries = filter_entries_by_month(
            all_entries,
            target_date.year,
            target_date.month
        )
        month_stats = aggregate_usage(month_entries)

        # Add to report
        report['apps'][app_name] = {
            'requests': today_stats['requests'],
            'total_tokens': today_stats['total_tokens'],
            'total_cost': today_stats['total_cost'],
            'errors': today_stats['errors'],
            'month_cost': month_stats['total_cost']
        }

        report['today_cost'] += today_stats['total_cost']
        report['month_cost'] += month_stats['total_cost']
        report['total_requests'] += today_stats['requests']
        report['total_errors'] += today_stats['errors']

        # Aggregate models
        for model, model_stats in today_stats['models'].items():
            report['models'][model]['calls'] += model_stats['calls']
            report['models'][model]['cost'] += model_stats['cost']

    # Convert defaultdict to regular dict
    report['models'] = dict(report['models'])

    return report


def check_thresholds(report):
    """Check if any thresholds are exceeded and send alerts"""
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


def main():
    """Main entry point"""
    print(f"Generating daily report at {datetime.now()}")

    # Generate report
    report = generate_report()

    print(f"Report generated:")
    print(f"  - Date: {report['date']}")
    print(f"  - Apps: {len(report['apps'])}")
    print(f"  - Today's cost: ${report['today_cost']:.2f}")
    print(f"  - Month-to-date: ${report['month_cost']:.2f}")

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
