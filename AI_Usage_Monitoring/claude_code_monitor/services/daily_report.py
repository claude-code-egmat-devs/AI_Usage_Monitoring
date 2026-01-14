"""
Daily Report Generator for Claude Code Monitor

Compiles all machine data and sends comprehensive daily report to Teams.
Designed to run via cron at end of day (11:30 PM IST / 18:00 UTC).
"""

import json
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.teams_notifier import send_daily_report
from lib.cost_calculator import format_cost, format_tokens

# Paths
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / 'logs'
MACHINES_FILE = LOGS_DIR / 'machines.json'
CONFIG_FILE = BASE_DIR / 'config' / 'config.json'


def load_config() -> Dict:
    """Load configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def load_machines() -> Dict:
    """Load machines registry."""
    if MACHINES_FILE.exists():
        with open(MACHINES_FILE, 'r') as f:
            return json.load(f)
    return {'machines': {}}


def get_daily_log_path(log_date: date = None) -> Path:
    """Get path to daily log file."""
    if log_date is None:
        log_date = date.today()
    return LOGS_DIR / f"usage_{log_date.isoformat()}.jsonl"


def get_daily_reports(log_date: date = None) -> List[Dict]:
    """Get all reports for a day."""
    log_path = get_daily_log_path(log_date)
    reports = []

    if log_path.exists():
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        reports.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    return reports


def compile_daily_data(log_date: date = None) -> Dict:
    """
    Compile all data for daily report.

    Returns formatted data ready for send_daily_report().
    """
    if log_date is None:
        log_date = date.today()

    reports = get_daily_reports(log_date)
    machines_registry = load_machines()
    config = load_config()
    thresholds = config.get('thresholds', {})

    # Group reports by machine (keep latest per machine)
    by_machine = {}
    for report in reports:
        machine_id = report.get('machine_id')
        if machine_id:
            by_machine[machine_id] = report

    # Aggregate by machine
    machines_summary = []
    all_sessions = []
    total_cost = 0
    total_tokens = 0
    session_count = 0

    for machine_id, report in by_machine.items():
        hostname = report.get('hostname', 'Unknown')
        cost = report.get('cost', {}).get('total_cost', 0)
        tokens_in = report.get('totals', {}).get('total_input_tokens', 0)
        tokens_out = report.get('totals', {}).get('total_output_tokens', 0)
        tokens = tokens_in + tokens_out
        sessions = report.get('sessions', [])

        total_cost += cost
        total_tokens += tokens
        session_count += len(sessions)

        machines_summary.append({
            'hostname': hostname,
            'sessions': len(sessions),
            'tokens': tokens,
            'cost': cost
        })

        # Collect sessions with machine info
        for session in sessions:
            all_sessions.append({
                'session_id': session.get('session_id', 'N/A'),
                'hostname': hostname,
                'model': session.get('model', 'unknown'),
                'thinking': session.get('thinking_enabled', False),
                'duration': session.get('duration_hours', 0),
                'tokens': (
                    session.get('input_tokens', 0) +
                    session.get('output_tokens', 0)
                ),
                'cost': session.get('cost_usd', 0)
            })

    # Sort machines by cost (descending)
    machines_summary.sort(key=lambda x: x['cost'], reverse=True)

    # Sort sessions by cost (descending)
    all_sessions.sort(key=lambda x: x['cost'], reverse=True)

    # Aggregate by model
    by_model = {}
    for report in by_machine.values():
        for model_name, model_data in report.get('by_model', {}).items():
            if model_name not in by_model:
                by_model[model_name] = {
                    'sessions': 0,
                    'tokens': 0,
                    'cost': 0
                }

            # Calculate cost for this model's tokens
            tokens_in = model_data.get('input_tokens', 0)
            tokens_out = model_data.get('output_tokens', 0)
            by_model[model_name]['tokens'] += tokens_in + tokens_out
            by_model[model_name]['sessions'] += model_data.get('sessions', 0)

            # Get cost from sessions with this model
            for session in report.get('sessions', []):
                if session.get('model') == model_name:
                    by_model[model_name]['cost'] += session.get('cost_usd', 0)

    return {
        'date': log_date.isoformat(),
        'total_cost': total_cost,
        'total_tokens': total_tokens,
        'session_count': session_count,
        'machines': machines_summary,
        'session_details': all_sessions[:10],  # Top 10 sessions
        'by_model': by_model,
        'thresholds': {
            'daily': thresholds.get('daily_limit_usd', 50),
            'weekly': thresholds.get('weekly_limit_usd', 250),
            'monthly': thresholds.get('monthly_limit_usd', 1000)
        }
    }


def generate_and_send_report(log_date: date = None) -> bool:
    """Generate and send the daily report."""
    print("=" * 60)
    print("Claude Code Monitor - Daily Report Generator")
    print("=" * 60)

    if log_date is None:
        log_date = date.today()

    print(f"\nGenerating report for: {log_date.isoformat()}")

    # Compile data
    report_data = compile_daily_data(log_date)

    # Display summary
    print(f"\nSummary:")
    print(f"  Sessions: {report_data['session_count']}")
    print(f"  Total tokens: {format_tokens(report_data['total_tokens'])}")
    print(f"  Total cost: {format_cost(report_data['total_cost'])}")
    print(f"  Machines reporting: {len(report_data['machines'])}")

    if report_data['machines']:
        print(f"\nBy Machine:")
        for m in report_data['machines']:
            print(f"  {m['hostname']}: {m['sessions']} sessions, {format_cost(m['cost'])}")

    if report_data['by_model']:
        print(f"\nBy Model:")
        for model, data in report_data['by_model'].items():
            short_name = model.replace('claude-', '').split('-202')[0]
            print(f"  {short_name}: {data['sessions']} sessions, {format_cost(data['cost'])}")

    # Send report
    print(f"\nSending to Teams...")
    success = send_daily_report(report_data)

    if success:
        print("Report sent successfully!")
    else:
        print("Failed to send report")

    return success


def print_report_preview(log_date: date = None):
    """Print report preview without sending."""
    if log_date is None:
        log_date = date.today()

    report_data = compile_daily_data(log_date)

    print("=" * 60)
    print(f"DAILY REPORT PREVIEW - {report_data['date']}")
    print("=" * 60)

    print(f"\nSUMMARY")
    print(f"  Sessions: {report_data['session_count']}")
    print(f"  Total tokens: {format_tokens(report_data['total_tokens'])}")
    print(f"  Total cost: {format_cost(report_data['total_cost'])}")
    daily_limit = report_data['thresholds']['daily']
    percent = (report_data['total_cost'] / daily_limit * 100) if daily_limit > 0 else 0
    print(f"  Budget: {format_cost(report_data['total_cost'])} / {format_cost(daily_limit)} ({percent:.0f}%)")

    print(f"\nBY MACHINE")
    for m in report_data['machines']:
        print(f"  {m['hostname']:20} | {m['sessions']:3} sessions | "
              f"{format_tokens(m['tokens']):>8} tokens | {format_cost(m['cost']):>8}")

    print(f"\nBY MODEL")
    for model, data in report_data['by_model'].items():
        short_name = model.replace('claude-', '').split('-202')[0]
        print(f"  {short_name:20} | {data['sessions']:3} sessions | {format_cost(data['cost']):>8}")

    print(f"\nTOP SESSIONS BY COST")
    for i, s in enumerate(report_data['session_details'][:5], 1):
        thinking = "Yes" if s['thinking'] else "No"
        print(f"  {i}. {s['hostname']} - {s['model'].replace('claude-', '').split('-202')[0]}")
        print(f"     Thinking: {thinking} | Duration: {s['duration']:.1f}h | "
              f"Tokens: {format_tokens(s['tokens'])} | Cost: {format_cost(s['cost'])}")


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Claude Code Monitor Daily Report')
    parser.add_argument(
        '--date',
        help='Date to report on (YYYY-MM-DD). Default: today'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview report without sending'
    )
    parser.add_argument(
        '--send',
        action='store_true',
        help='Generate and send the report'
    )

    args = parser.parse_args()

    # Parse date
    log_date = None
    if args.date:
        try:
            log_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
            sys.exit(1)

    if args.preview:
        print_report_preview(log_date)
    elif args.send:
        success = generate_and_send_report(log_date)
        sys.exit(0 if success else 1)
    else:
        # Default: preview
        print_report_preview(log_date)
        print("\nUse --send to actually send the report")
