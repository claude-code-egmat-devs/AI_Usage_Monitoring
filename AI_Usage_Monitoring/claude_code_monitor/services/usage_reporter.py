"""
Usage Reporter for Claude Code Monitor

Runs on each machine (Windows/Linux) to collect usage data and send to central aggregator.
Handles machine registration, usage reporting, and offline queuing.
"""

import json
import os
import sys
import socket
import platform
import uuid
import requests
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.claude_usage_reader import get_todays_usage, get_claude_dir
from lib.cost_calculator import calculate_session_cost, calculate_daily_cost


# Machine ID storage location
def get_machine_id_path() -> Path:
    """Get path to machine ID file."""
    if os.name == 'nt':  # Windows
        base = Path(os.path.expanduser("~/.claude-monitor"))
    else:  # Linux/Mac
        base = Path.home() / ".claude-monitor"

    base.mkdir(parents=True, exist_ok=True)
    return base / "machine_id"


def get_queue_path() -> Path:
    """Get path to offline queue file."""
    base = get_machine_id_path().parent
    return base / "queue.jsonl"


def get_or_create_machine_id() -> str:
    """Get existing machine ID or create a new one."""
    id_path = get_machine_id_path()

    if id_path.exists():
        with open(id_path, 'r') as f:
            return f.read().strip()

    # Generate new ID
    machine_id = str(uuid.uuid4())
    with open(id_path, 'w') as f:
        f.write(machine_id)

    return machine_id


def get_machine_info() -> Dict:
    """Collect information about this machine."""
    machine_id = get_or_create_machine_id()

    try:
        username = os.getlogin()
    except Exception:
        username = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))

    return {
        'machine_id': machine_id,
        'hostname': socket.gethostname(),
        'username': username,
        'os': platform.system(),
        'os_version': platform.version(),
        'python_version': platform.python_version()
    }


def is_new_machine(machine_id: str, aggregator_url: str) -> bool:
    """Check if this machine is new (not yet registered)."""
    id_path = get_machine_id_path()
    registered_path = id_path.parent / "registered"

    # If we have a local "registered" flag, we're not new
    if registered_path.exists():
        return False

    # Try to check with aggregator
    try:
        response = requests.get(
            f"{aggregator_url}/machines/{machine_id}",
            timeout=10
        )
        if response.status_code == 200:
            # Machine exists, mark as registered locally
            registered_path.touch()
            return False
        elif response.status_code == 404:
            return True
    except Exception:
        pass

    return True


def register_machine(aggregator_url: str) -> bool:
    """Register this machine with the aggregator."""
    machine_info = get_machine_info()
    machine_info['first_seen'] = datetime.utcnow().isoformat() + 'Z'

    try:
        response = requests.post(
            f"{aggregator_url}/register",
            json=machine_info,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            # Mark as registered locally
            registered_path = get_machine_id_path().parent / "registered"
            registered_path.touch()
            print(f"Machine registered successfully: {machine_info['hostname']}")
            return True
        else:
            print(f"Registration failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"Error registering machine: {e}")
        return False


def collect_usage_data() -> Dict:
    """Collect today's usage data from Claude Code."""
    machine_info = get_machine_info()

    # Get usage data
    usage = get_todays_usage()

    # Calculate costs for each session
    sessions_with_cost = []
    for session in usage.get('sessions', []):
        cost = calculate_session_cost(session)
        session_data = {
            **session,
            'cost_usd': cost.total_cost,
            'cost_breakdown': {
                'input': cost.input_cost,
                'output': cost.output_cost,
                'cache_read': cost.cache_read_cost,
                'cache_write': cost.cache_write_cost
            }
        }
        sessions_with_cost.append(session_data)

    # Calculate total cost
    cost_data = calculate_daily_cost(usage)

    return {
        'machine_id': machine_info['machine_id'],
        'hostname': machine_info['hostname'],
        'username': machine_info['username'],
        'os': machine_info['os'],
        'date': usage.get('date', date.today().isoformat()),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'sessions': sessions_with_cost,
        'totals': usage.get('totals', {}),
        'by_model': usage.get('by_model', {}),
        'cost': cost_data.get('total', {}),
        'daily_stats': usage.get('daily_stats', {})
    }


def queue_report(report_data: Dict):
    """Queue report for later submission (offline mode)."""
    queue_path = get_queue_path()

    with open(queue_path, 'a') as f:
        f.write(json.dumps(report_data) + '\n')

    print(f"Report queued for later submission")


def submit_queued_reports(aggregator_url: str) -> int:
    """Submit any queued reports. Returns count of successfully submitted."""
    queue_path = get_queue_path()

    if not queue_path.exists():
        return 0

    submitted = 0
    remaining = []

    with open(queue_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                report = json.loads(line)
                response = requests.post(
                    f"{aggregator_url}/report",
                    json=report,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

                if response.status_code == 200:
                    submitted += 1
                else:
                    remaining.append(line)
            except Exception:
                remaining.append(line)

    # Rewrite queue with remaining items
    if remaining:
        with open(queue_path, 'w') as f:
            f.write('\n'.join(remaining) + '\n')
    else:
        queue_path.unlink()

    return submitted


def send_report(aggregator_url: str, report_data: Dict) -> bool:
    """Send usage report to aggregator."""
    try:
        response = requests.post(
            f"{aggregator_url}/report",
            json=report_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            print("Report sent successfully")
            return True
        else:
            print(f"Report failed: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("Aggregator unreachable - queuing report")
        queue_report(report_data)
        return False
    except Exception as e:
        print(f"Error sending report: {e}")
        queue_report(report_data)
        return False


def run_reporter(aggregator_url: str):
    """
    Main reporter function.

    1. Check if machine is registered, register if new
    2. Collect usage data
    3. Send to aggregator (or queue if offline)
    4. Submit any previously queued reports
    """
    print("=" * 60)
    print("Claude Code Usage Reporter")
    print("=" * 60)

    machine_info = get_machine_info()
    print(f"\nMachine: {machine_info['hostname']}")
    print(f"User: {machine_info['username']}")
    print(f"OS: {machine_info['os']}")
    print(f"Machine ID: {machine_info['machine_id'][:8]}...")

    # Check registration
    if is_new_machine(machine_info['machine_id'], aggregator_url):
        print("\nNew machine detected - registering...")
        register_machine(aggregator_url)

    # Collect usage data
    print("\nCollecting usage data...")
    report_data = collect_usage_data()

    print(f"\nToday's stats:")
    print(f"  Sessions: {len(report_data.get('sessions', []))}")
    print(f"  Total tokens: {report_data.get('totals', {}).get('total_input_tokens', 0):,} in / "
          f"{report_data.get('totals', {}).get('total_output_tokens', 0):,} out")
    print(f"  Total cost: ${report_data.get('cost', {}).get('total_cost', 0):.2f}")

    # Send report
    print(f"\nSending to aggregator: {aggregator_url}")
    send_report(aggregator_url, report_data)

    # Submit queued reports
    queued = submit_queued_reports(aggregator_url)
    if queued > 0:
        print(f"Submitted {queued} previously queued reports")

    print("\nDone.")


def load_config() -> Dict:
    """Load configuration file."""
    config_path = Path(__file__).parent.parent / 'config' / 'config.json'
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Claude Code Usage Reporter')
    parser.add_argument(
        '--aggregator-url',
        default=os.environ.get('AGGREGATOR_URL', 'http://localhost:8011'),
        help='URL of the central aggregator service'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Collect and display data without sending'
    )

    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print("Claude Code Usage Reporter - DRY RUN")
        print("=" * 60)

        machine_info = get_machine_info()
        print(f"\nMachine Info:")
        for key, value in machine_info.items():
            print(f"  {key}: {value}")

        print("\nCollecting usage data...")
        report = collect_usage_data()

        print(f"\nReport Data:")
        print(f"  Date: {report.get('date')}")
        print(f"  Sessions: {len(report.get('sessions', []))}")
        print(f"  Totals: {json.dumps(report.get('totals', {}), indent=4)}")
        print(f"  Cost: {json.dumps(report.get('cost', {}), indent=4)}")

        if report.get('sessions'):
            print(f"\nSession Details:")
            for s in report['sessions'][:3]:
                print(f"\n  {s.get('session_id', 'N/A')[:8]}...")
                print(f"    Model: {s.get('model', 'N/A')}")
                print(f"    Cost: ${s.get('cost_usd', 0):.4f}")
                print(f"    Duration: {s.get('duration_hours', 0):.2f}h")
    else:
        # Load config for aggregator URL if not provided
        config = load_config()
        aggregator_url = args.aggregator_url
        if aggregator_url == 'http://localhost:8011':
            aggregator_url = config.get('aggregator', {}).get('url', aggregator_url)

        run_reporter(aggregator_url)
