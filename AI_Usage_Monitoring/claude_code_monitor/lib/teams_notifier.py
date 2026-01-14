"""
Teams Notifier for Claude Code Usage Monitor

Sends notifications to Microsoft Teams via Power Automate.
Supports daily reports, threshold alerts, and new machine notifications.
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Config path relative to this file
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'config',
    'config.json'
)


def load_config() -> Dict:
    """Load configuration from config file."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def get_teams_config() -> Dict:
    """Get Teams configuration, supporting both env vars and config file."""
    config = load_config()
    teams_config = config.get('teams', {})

    # Environment variables take precedence
    return {
        'power_automate_url': os.environ.get(
            'POWER_AUTOMATE_URL',
            teams_config.get('power_automate_url', '')
        ),
        'chat_id': os.environ.get(
            'TEAMS_CHAT_ID',
            teams_config.get('chat_id', '')
        ),
        'agent_email': os.environ.get(
            'AGENT_EMAIL',
            teams_config.get('agent_email', '')
        )
    }


def send_teams_message(message: str, message_type: str = "info") -> bool:
    """
    Send a message to Teams via Power Automate.

    Args:
        message: The message body (supports HTML/markdown)
        message_type: "info", "warning", "critical", "error", "success"

    Returns:
        bool: True if successful, False otherwise
    """
    teams_config = get_teams_config()

    url = teams_config.get('power_automate_url')
    chat_id = teams_config.get('chat_id')
    agent_email = teams_config.get('agent_email')

    if not url or url == "PLACEHOLDER_URL":
        print("Warning: Power Automate URL not configured")
        return False

    # Add emoji prefix based on type
    emoji_map = {
        "info": "📊",
        "warning": "⚠️",
        "critical": "🚨",
        "error": "❌",
        "success": "✅",
        "new": "🆕"
    }
    emoji = emoji_map.get(message_type, "📢")

    # Prepare payload
    payload = {
        "chat_id": chat_id,
        "agent_email": agent_email,
        "message_body": f"{emoji} {message}"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            print(f"Teams notification sent: {message_type}")
            return True
        else:
            print(f"Teams notification failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"Error sending Teams notification: {e}")
        return False


def format_cost(amount: float) -> str:
    """Format cost for display."""
    return f"${amount:.2f}"


def format_tokens(count: int) -> str:
    """Format token count for display."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def send_new_machine_alert(machine_info: Dict) -> bool:
    """
    Send notification when a new machine registers.

    Args:
        machine_info: {machine_id, hostname, username, os, first_seen}
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')

    message = f"""<b>New Claude Code Machine Registered</b>

<b>Time:</b> {timestamp}
<b>Hostname:</b> {machine_info.get('hostname', 'Unknown')}
<b>Username:</b> {machine_info.get('username', 'Unknown')}
<b>OS:</b> {machine_info.get('os', 'Unknown')}
<b>Machine ID:</b> {machine_info.get('machine_id', 'Unknown')[:8]}...

This machine will now be tracked in daily usage reports."""

    return send_teams_message(message, "new")


def send_threshold_alert(
    alert_type: str,
    current_cost: float,
    threshold: float,
    details: Dict
) -> bool:
    """
    Send threshold breach alert.

    Args:
        alert_type: "daily_warning", "daily_critical", "weekly", "monthly"
        current_cost: Current spend amount
        threshold: Threshold that was crossed
        details: Additional context (machines, top sessions)
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')
    percent = (current_cost / threshold * 100) if threshold > 0 else 0

    # Build machines breakdown
    machines_breakdown = ""
    if 'machines' in details:
        machines_breakdown = "\n<b>Breakdown by Machine:</b>\n<table>\n"
        machines_breakdown += "<tr><th>Machine</th><th>Sessions</th><th>Cost</th></tr>\n"
        for machine in details['machines']:
            machines_breakdown += (
                f"<tr><td>{machine['hostname']}</td>"
                f"<td>{machine['sessions']}</td>"
                f"<td>{format_cost(machine['cost'])}</td></tr>\n"
            )
        machines_breakdown += "</table>"

    # Build top sessions list
    top_sessions = ""
    if 'top_sessions' in details:
        top_sessions = "\n<b>Top Sessions by Cost:</b>\n"
        for i, session in enumerate(details['top_sessions'][:3], 1):
            top_sessions += (
                f"{i}. {session['hostname']} - {session['model']}\n"
                f"   Cost: {format_cost(session['cost'])} | "
                f"Duration: {session.get('duration', 0):.1f}h\n"
            )

    if alert_type == "daily_warning":
        title = "CLAUDE CODE USAGE WARNING"
        msg_type = "warning"
        action = "Consider reviewing active sessions"
    elif alert_type == "daily_critical":
        title = "CLAUDE CODE USAGE CRITICAL"
        msg_type = "critical"
        action = "Immediate review recommended - pause non-critical work"
    elif alert_type == "weekly":
        title = "WEEKLY BUDGET WARNING"
        msg_type = "warning"
        action = "Weekly budget approaching limit"
    else:
        title = "MONTHLY BUDGET ALERT"
        msg_type = "critical"
        action = "Monthly budget nearly exhausted"

    message = f"""<b>{title}</b>

<b>Time:</b> {timestamp}
<b>Current Spend:</b> {format_cost(current_cost)} / {format_cost(threshold)} ({percent:.0f}%)
{machines_breakdown}
{top_sessions}
<b>Action:</b> {action}"""

    return send_teams_message(message, msg_type)


def send_daily_report(report_data: Dict) -> bool:
    """
    Send comprehensive daily usage report.

    Args:
        report_data: {
            date, total_cost, total_tokens, sessions,
            machines: [{hostname, sessions, cost, tokens}],
            session_details: [{session_id, hostname, model, cost, duration, thinking}],
            by_model: {model: {cost, tokens, sessions}},
            thresholds: {daily, weekly, monthly}
        }
    """
    date_str = report_data.get('date', datetime.now().strftime('%Y-%m-%d'))
    total_cost = report_data.get('total_cost', 0)
    total_tokens = report_data.get('total_tokens', 0)
    session_count = report_data.get('session_count', 0)

    # Machines table
    machines = report_data.get('machines', [])
    machines_table = """<table>
<tr><th>Machine</th><th>Sessions</th><th>Tokens</th><th>Cost</th></tr>
"""
    for machine in machines:
        machines_table += (
            f"<tr><td>{machine.get('hostname', 'Unknown')}</td>"
            f"<td>{machine.get('sessions', 0)}</td>"
            f"<td>{format_tokens(machine.get('tokens', 0))}</td>"
            f"<td>{format_cost(machine.get('cost', 0))}</td></tr>\n"
        )
    machines_table += "</table>"

    # Models table
    by_model = report_data.get('by_model', {})
    models_table = """<table>
<tr><th>Model</th><th>Sessions</th><th>Cost</th></tr>
"""
    for model_name, model_data in by_model.items():
        # Shorten model name
        short_name = model_name.replace('claude-', '').split('-202')[0]
        models_table += (
            f"<tr><td>{short_name}</td>"
            f"<td>{model_data.get('sessions', 0)}</td>"
            f"<td>{format_cost(model_data.get('cost', 0))}</td></tr>\n"
        )
    models_table += "</table>"

    # Top sessions
    sessions = report_data.get('session_details', [])
    sessions_sorted = sorted(sessions, key=lambda x: x.get('cost', 0), reverse=True)
    top_sessions_text = ""
    for i, s in enumerate(sessions_sorted[:5], 1):
        thinking_str = "Yes" if s.get('thinking', False) else "No"
        model_short = s.get('model', 'unknown').replace('claude-', '').split('-202')[0]
        top_sessions_text += (
            f"{i}. <b>{s.get('hostname', 'Unknown')}</b>\n"
            f"   Model: {model_short} | Thinking: {thinking_str}\n"
            f"   Duration: {s.get('duration', 0):.1f}h | "
            f"Tokens: {format_tokens(s.get('tokens', 0))} | "
            f"Cost: {format_cost(s.get('cost', 0))}\n\n"
        )

    # Budget status
    thresholds = report_data.get('thresholds', {})
    daily_limit = thresholds.get('daily', 50)
    daily_percent = (total_cost / daily_limit * 100) if daily_limit > 0 else 0

    if daily_percent >= 90:
        status = "🚨 CRITICAL"
        msg_type = "critical"
    elif daily_percent >= 70:
        status = "⚠️ WARNING"
        msg_type = "warning"
    else:
        status = "✅ Normal"
        msg_type = "info"

    message = f"""<b>CLAUDE CODE DAILY USAGE REPORT - {date_str}</b>

<b>📊 Summary</b>
<table>
<tr><td>Total Sessions</td><td><b>{session_count}</b></td></tr>
<tr><td>Total Tokens</td><td><b>{format_tokens(total_tokens)}</b></td></tr>
<tr><td>Total Cost</td><td><b>{format_cost(total_cost)}</b></td></tr>
<tr><td>Daily Budget</td><td>{format_cost(total_cost)} / {format_cost(daily_limit)} ({daily_percent:.0f}%)</td></tr>
<tr><td>Status</td><td><b>{status}</b></td></tr>
</table>

<b>📍 By Machine</b>
{machines_table}

<b>🤖 By Model</b>
{models_table}

<b>📋 Top Sessions by Cost</b>
{top_sessions_text}"""

    return send_teams_message(message, msg_type)


def send_error_alert(error_message: str, context: Dict = None) -> bool:
    """Send error alert when something goes wrong."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')

    context_str = ""
    if context:
        context_str = "\n<b>Context:</b>\n"
        for key, value in context.items():
            context_str += f"- {key}: {value}\n"

    message = f"""<b>Claude Code Monitor Error</b>

<b>Time:</b> {timestamp}
<b>Error:</b> {error_message}
{context_str}
Please investigate."""

    return send_teams_message(message, "error")


# CLI for testing
if __name__ == "__main__":
    print("=" * 60)
    print("Teams Notifier - Test Mode")
    print("=" * 60)

    # Test basic message
    print("\nTesting basic message...")
    result = send_teams_message(
        "🧪 Test message from Claude Code Monitor",
        "info"
    )
    print(f"Result: {'Success' if result else 'Failed'}")

    # Show config status
    config = get_teams_config()
    print(f"\nConfig status:")
    print(f"  URL configured: {'Yes' if config.get('power_automate_url') else 'No'}")
    print(f"  Chat ID configured: {'Yes' if config.get('chat_id') else 'No'}")
