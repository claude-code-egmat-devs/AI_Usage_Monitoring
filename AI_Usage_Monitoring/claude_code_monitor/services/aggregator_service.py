"""
Central Aggregator Service for Claude Code Monitor

Flask-based service that:
- Receives usage reports from all machines
- Manages machine registry
- Stores daily usage logs
- Checks thresholds and triggers alerts
- Provides status endpoints

Runs on VPS at port 8011.
"""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
from flask import Flask, request, jsonify
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.teams_notifier import (
    send_new_machine_alert,
    send_threshold_alert,
    send_error_alert
)

app = Flask(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / 'logs'
MACHINES_FILE = LOGS_DIR / 'machines.json'
ALERT_STATE_FILE = LOGS_DIR / 'alert_state.json'
CONFIG_FILE = BASE_DIR / 'config' / 'config.json'

# Ensure directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)


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


def save_machines(machines: Dict):
    """Save machines registry."""
    with open(MACHINES_FILE, 'w') as f:
        json.dump(machines, f, indent=2)


def load_alert_state() -> Dict:
    """Load alert state (tracks which alerts have been sent)."""
    if ALERT_STATE_FILE.exists():
        with open(ALERT_STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_alert_state(state: Dict):
    """Save alert state."""
    with open(ALERT_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_daily_log_path(log_date: date = None) -> Path:
    """Get path to daily log file."""
    if log_date is None:
        log_date = date.today()
    return LOGS_DIR / f"usage_{log_date.isoformat()}.jsonl"


def append_to_daily_log(report: Dict):
    """Append report to daily log."""
    log_path = get_daily_log_path()
    with open(log_path, 'a') as f:
        f.write(json.dumps(report) + '\n')


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


def calculate_daily_totals(reports: List[Dict]) -> Dict:
    """Calculate totals from all reports for a day."""
    # Group by machine (latest report per machine)
    by_machine = {}
    for report in reports:
        machine_id = report.get('machine_id')
        if machine_id:
            by_machine[machine_id] = report

    # Aggregate
    total_cost = 0
    total_sessions = 0
    total_tokens = 0
    machines_summary = []

    for machine_id, report in by_machine.items():
        cost = report.get('cost', {}).get('total_cost', 0)
        sessions = len(report.get('sessions', []))
        tokens = (
            report.get('totals', {}).get('total_input_tokens', 0) +
            report.get('totals', {}).get('total_output_tokens', 0)
        )

        total_cost += cost
        total_sessions += sessions
        total_tokens += tokens

        machines_summary.append({
            'machine_id': machine_id,
            'hostname': report.get('hostname', 'Unknown'),
            'sessions': sessions,
            'cost': cost,
            'tokens': tokens
        })

    return {
        'total_cost': total_cost,
        'total_sessions': total_sessions,
        'total_tokens': total_tokens,
        'machines': machines_summary,
        'machine_count': len(by_machine)
    }


def check_thresholds(totals: Dict) -> List[Dict]:
    """Check if any thresholds are exceeded. Returns list of alerts to send."""
    config = load_config()
    thresholds = config.get('thresholds', {})
    alert_state = load_alert_state()
    today_str = date.today().isoformat()

    alerts_to_send = []
    total_cost = totals.get('total_cost', 0)

    # Daily warning (70% of daily limit)
    daily_limit = thresholds.get('daily_limit_usd', 50)
    daily_warning = thresholds.get('daily_warning_usd', daily_limit * 0.7)
    daily_critical = thresholds.get('daily_critical_usd', daily_limit * 0.9)

    # Check daily warning
    warning_key = f"daily_warning_{today_str}"
    if total_cost >= daily_warning and warning_key not in alert_state:
        alerts_to_send.append({
            'type': 'daily_warning',
            'current_cost': total_cost,
            'threshold': daily_warning,
            'key': warning_key
        })

    # Check daily critical
    critical_key = f"daily_critical_{today_str}"
    if total_cost >= daily_critical and critical_key not in alert_state:
        alerts_to_send.append({
            'type': 'daily_critical',
            'current_cost': total_cost,
            'threshold': daily_critical,
            'key': critical_key
        })

    return alerts_to_send


def send_pending_alerts(alerts: List[Dict], totals: Dict):
    """Send pending alerts and update state."""
    if not alerts:
        return

    alert_state = load_alert_state()

    for alert in alerts:
        details = {
            'machines': totals.get('machines', []),
            'top_sessions': []  # Would need session data for this
        }

        success = send_threshold_alert(
            alert_type=alert['type'],
            current_cost=alert['current_cost'],
            threshold=alert['threshold'],
            details=details
        )

        if success:
            alert_state[alert['key']] = datetime.utcnow().isoformat()

    save_alert_state(alert_state)


# Flask Routes

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/register', methods=['POST'])
def register_machine():
    """Register a new machine."""
    data = request.get_json()

    if not data or 'machine_id' not in data:
        return jsonify({'error': 'machine_id required'}), 400

    machines = load_machines()
    machine_id = data['machine_id']

    is_new = machine_id not in machines.get('machines', {})

    # Add/update machine
    machines.setdefault('machines', {})[machine_id] = {
        'hostname': data.get('hostname', 'Unknown'),
        'username': data.get('username', 'Unknown'),
        'os': data.get('os', 'Unknown'),
        'first_seen': data.get('first_seen', datetime.utcnow().isoformat() + 'Z'),
        'last_seen': datetime.utcnow().isoformat() + 'Z'
    }

    save_machines(machines)

    # Send Teams alert for new machine
    if is_new:
        send_new_machine_alert({
            'machine_id': machine_id,
            'hostname': data.get('hostname', 'Unknown'),
            'username': data.get('username', 'Unknown'),
            'os': data.get('os', 'Unknown')
        })

    return jsonify({
        'status': 'registered',
        'machine_id': machine_id,
        'is_new': is_new
    })


@app.route('/machines/<machine_id>', methods=['GET'])
def get_machine(machine_id: str):
    """Get machine info."""
    machines = load_machines()

    if machine_id in machines.get('machines', {}):
        return jsonify(machines['machines'][machine_id])
    else:
        return jsonify({'error': 'Machine not found'}), 404


@app.route('/machines', methods=['GET'])
def list_machines():
    """List all registered machines."""
    machines = load_machines()
    return jsonify(machines)


@app.route('/report', methods=['POST'])
def receive_report():
    """Receive usage report from a machine."""
    data = request.get_json()

    if not data or 'machine_id' not in data:
        return jsonify({'error': 'machine_id required'}), 400

    # Update machine last_seen
    machines = load_machines()
    machine_id = data['machine_id']

    if machine_id in machines.get('machines', {}):
        machines['machines'][machine_id]['last_seen'] = datetime.utcnow().isoformat() + 'Z'
        save_machines(machines)

    # Append to daily log
    append_to_daily_log(data)

    # Check thresholds
    reports = get_daily_reports()
    totals = calculate_daily_totals(reports)
    alerts = check_thresholds(totals)
    send_pending_alerts(alerts, totals)

    return jsonify({
        'status': 'received',
        'machine_id': machine_id,
        'daily_total_cost': totals.get('total_cost', 0),
        'alerts_triggered': len(alerts)
    })


@app.route('/status', methods=['GET'])
def get_status():
    """Get current status and daily totals."""
    reports = get_daily_reports()
    totals = calculate_daily_totals(reports)
    machines = load_machines()
    config = load_config()

    thresholds = config.get('thresholds', {})
    daily_limit = thresholds.get('daily_limit_usd', 50)

    return jsonify({
        'date': date.today().isoformat(),
        'totals': totals,
        'daily_limit': daily_limit,
        'usage_percent': (totals.get('total_cost', 0) / daily_limit * 100) if daily_limit > 0 else 0,
        'registered_machines': len(machines.get('machines', {})),
        'reporting_machines': totals.get('machine_count', 0)
    })


@app.route('/reports/<report_date>', methods=['GET'])
def get_reports_for_date(report_date: str):
    """Get all reports for a specific date."""
    try:
        target_date = date.fromisoformat(report_date)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    reports = get_daily_reports(target_date)
    totals = calculate_daily_totals(reports)

    return jsonify({
        'date': report_date,
        'reports': reports,
        'totals': totals
    })


def run_server(host: str = '0.0.0.0', port: int = 8011, debug: bool = False):
    """Run the aggregator server."""
    print("=" * 60)
    print("Claude Code Monitor - Aggregator Service")
    print("=" * 60)
    print(f"\nStarting server on {host}:{port}")
    print(f"Logs directory: {LOGS_DIR}")
    print(f"Machines file: {MACHINES_FILE}")

    app.run(host=host, port=port, debug=debug)


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Claude Code Monitor Aggregator')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8011, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    run_server(host=args.host, port=args.port, debug=args.debug)
