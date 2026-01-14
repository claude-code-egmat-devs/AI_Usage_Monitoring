#!/usr/bin/env python3
"""
Alert Monitor Service
Checks for threshold breaches and sends alerts
Can be run as a cron job (e.g., every hour) or as a continuous service
"""
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib'))

from teams_notifier import send_alert, load_settings


# Track alerts to avoid duplicates
ALERT_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'logs',
    'alert_state.json'
)


def load_alert_state():
    """Load previous alert state to avoid duplicate alerts"""
    if os.path.exists(ALERT_STATE_FILE):
        try:
            with open(ALERT_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_alert_state(state):
    """Save alert state"""
    os.makedirs(os.path.dirname(ALERT_STATE_FILE), exist_ok=True)
    with open(ALERT_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def read_all_logs(apps_config):
    """Read logs from all configured apps"""
    all_entries = []
    for app_name, app_config in apps_config.items():
        log_file = app_config.get('log_file')
        if not log_file or not os.path.exists(log_file):
            continue

        try:
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            entry['_app_name'] = app_name
                            all_entries.append(entry)
                        except:
                            continue
        except Exception as e:
            print(f"Error reading {log_file}: {e}")

    return all_entries


def get_today_cost(entries):
    """Calculate total cost for today"""
    today = datetime.now().strftime('%Y-%m-%d')
    total = 0.0
    for entry in entries:
        if entry.get('timestamp', '').startswith(today):
            total += entry.get('cost_usd', 0) or 0
    return total


def get_month_cost(entries):
    """Calculate total cost for current month"""
    month_prefix = datetime.now().strftime('%Y-%m')
    total = 0.0
    for entry in entries:
        if entry.get('timestamp', '').startswith(month_prefix):
            total += entry.get('cost_usd', 0) or 0
    return total


def get_recent_errors(entries, window_minutes=60):
    """Get errors in the last N minutes"""
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    cutoff_str = cutoff.isoformat() + 'Z'

    errors = []
    for entry in entries:
        if not entry.get('success', True):
            timestamp = entry.get('timestamp', '')
            if timestamp >= cutoff_str:
                errors.append(entry)

    return errors


def check_alerts():
    """Main alert checking function"""
    settings = load_settings()
    thresholds = settings.get('thresholds', {})
    apps_config = settings.get('apps', {})

    # Load previous alert state
    alert_state = load_alert_state()
    today = datetime.now().strftime('%Y-%m-%d')

    # Read all logs
    entries = read_all_logs(apps_config)

    alerts_sent = []

    # Check daily cost
    today_cost = get_today_cost(entries)
    daily_critical = thresholds.get('daily_critical_usd', 10)
    daily_warning = thresholds.get('daily_warning_usd', 5)

    # Check if we already sent this alert today
    daily_alert_key = f"daily_{today}"

    if today_cost >= daily_critical:
        if alert_state.get(daily_alert_key) != 'critical':
            send_alert('daily_critical', {
                'cost': today_cost,
                'threshold': daily_critical
            })
            alert_state[daily_alert_key] = 'critical'
            alerts_sent.append('daily_critical')
    elif today_cost >= daily_warning:
        if alert_state.get(daily_alert_key) not in ['warning', 'critical']:
            send_alert('daily_warning', {
                'cost': today_cost,
                'threshold': daily_warning
            })
            alert_state[daily_alert_key] = 'warning'
            alerts_sent.append('daily_warning')

    # Check monthly budget
    month_cost = get_month_cost(entries)
    monthly_budget = thresholds.get('monthly_budget_usd', 100)
    budget_alert_percent = thresholds.get('budget_alert_percent', 80)
    month_key = datetime.now().strftime('%Y-%m')
    budget_alert_key = f"budget_{month_key}"

    if monthly_budget > 0:
        usage_percent = (month_cost / monthly_budget) * 100
        if usage_percent >= budget_alert_percent:
            if not alert_state.get(budget_alert_key):
                send_alert('budget_warning', {
                    'spent': month_cost,
                    'budget': monthly_budget,
                    'percent': usage_percent
                })
                alert_state[budget_alert_key] = True
                alerts_sent.append('budget_warning')

    # Check error spikes
    error_alert_count = thresholds.get('error_alert_count', 5)
    error_window = thresholds.get('error_alert_window_minutes', 60)
    recent_errors = get_recent_errors(entries, error_window)

    if len(recent_errors) >= error_alert_count:
        # Group by app
        error_apps = defaultdict(list)
        for err in recent_errors:
            error_apps[err.get('_app_name', 'Unknown')].append(err)

        for app_name, app_errors in error_apps.items():
            if len(app_errors) >= error_alert_count:
                error_alert_key = f"error_{app_name}_{today}"
                if not alert_state.get(error_alert_key):
                    send_alert('error_spike', {
                        'error_count': len(app_errors),
                        'app': app_name,
                        'last_error': app_errors[-1].get('error', 'Unknown')[:100]
                    })
                    alert_state[error_alert_key] = True
                    alerts_sent.append(f'error_spike_{app_name}')

    # Clean up old alert state (keep last 7 days)
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    alert_state = {
        k: v for k, v in alert_state.items()
        if not k.startswith('daily_') or k.split('_')[1] >= week_ago
    }

    # Save state
    save_alert_state(alert_state)

    return {
        'today_cost': today_cost,
        'month_cost': month_cost,
        'alerts_sent': alerts_sent
    }


def main():
    """Main entry point"""
    print(f"Running alert check at {datetime.now()}")

    result = check_alerts()

    print(f"Today's cost: ${result['today_cost']:.2f}")
    print(f"Month-to-date: ${result['month_cost']:.2f}")
    print(f"Alerts sent: {result['alerts_sent'] or 'None'}")


if __name__ == "__main__":
    main()
