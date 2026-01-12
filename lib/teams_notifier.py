"""
Teams Notifier Module
Sends notifications to Microsoft Teams via Power Automate
"""
import json
import os
import requests
from datetime import datetime

# Load settings
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.json')


def load_settings():
    """Load settings from config file"""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def send_teams_message(message, message_type="info"):
    """
    Send a message to Teams via Power Automate

    Args:
        message: The message body (supports markdown)
        message_type: "info", "warning", "critical", "error"

    Returns:
        bool: True if successful, False otherwise
    """
    settings = load_settings()
    teams_config = settings.get('teams', {})

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
        "success": "✅"
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
            print(f"Teams notification sent successfully: {message_type}")
            return True
        else:
            print(f"Teams notification failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"Error sending Teams notification: {e}")
        return False


def send_daily_report(report_data):
    """
    Send daily usage report to Teams

    Args:
        report_data: Dictionary containing report data
    """
    date_str = report_data.get('date', datetime.now().strftime('%Y-%m-%d'))

    message = f"""**AI Usage Daily Report - {date_str}**

**📱 Apps Summary:**
"""

    # Add app breakdown
    apps = report_data.get('apps', {})
    for app_name, app_data in apps.items():
        requests_count = app_data.get('requests', 0)
        tokens = app_data.get('total_tokens', 0)
        cost = app_data.get('total_cost', 0)
        message += f"\n• **{app_name}**: {requests_count} requests | {tokens:,} tokens | ${cost:.2f}"

    # Add model breakdown
    message += "\n\n**📈 Model Usage:**"
    models = report_data.get('models', {})
    for model_name, model_data in models.items():
        calls = model_data.get('calls', 0)
        cost = model_data.get('cost', 0)
        short_name = model_name.replace('claude-', '').replace('-20250929', '').replace('-20251001', '')
        message += f"\n• {short_name}: {calls} calls (${cost:.2f})"

    # Add budget status
    today_cost = report_data.get('today_cost', 0)
    month_cost = report_data.get('month_cost', 0)
    budget = report_data.get('budget', 100)
    budget_percent = (month_cost / budget * 100) if budget > 0 else 0

    message += f"""

**💰 Budget Status:**
• Today: ${today_cost:.2f}
• Month-to-date: ${month_cost:.2f} / ${budget:.2f} ({budget_percent:.0f}%)
"""

    # Add status
    settings = load_settings()
    thresholds = settings.get('thresholds', {})
    daily_warning = thresholds.get('daily_warning_usd', 5)
    daily_critical = thresholds.get('daily_critical_usd', 10)

    if today_cost >= daily_critical:
        status = "🚨 **CRITICAL** - Daily cost exceeded critical threshold!"
        msg_type = "critical"
    elif today_cost >= daily_warning:
        status = "⚠️ **WARNING** - Daily cost exceeded warning threshold"
        msg_type = "warning"
    else:
        status = "✅ **Normal** - All within limits"
        msg_type = "info"

    message += f"\n**Status:** {status}"

    return send_teams_message(message, msg_type)


def send_alert(alert_type, details):
    """
    Send an alert to Teams

    Args:
        alert_type: "daily_warning", "daily_critical", "budget_warning", "error_spike"
        details: Dictionary with alert details
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')

    if alert_type == "daily_warning":
        message = f"""**Daily Cost Warning**

**Time:** {timestamp}
**Today's Cost:** ${details.get('cost', 0):.2f}
**Threshold:** ${details.get('threshold', 5):.2f}

Please review usage if unexpected.
"""
        return send_teams_message(message, "warning")

    elif alert_type == "daily_critical":
        message = f"""**CRITICAL: Daily Cost Alert**

**Time:** {timestamp}
**Today's Cost:** ${details.get('cost', 0):.2f}
**Threshold:** ${details.get('threshold', 10):.2f}

⚠️ Immediate review recommended!
"""
        return send_teams_message(message, "critical")

    elif alert_type == "budget_warning":
        message = f"""**Budget Alert**

**Time:** {timestamp}
**Month-to-date:** ${details.get('spent', 0):.2f}
**Monthly Budget:** ${details.get('budget', 100):.2f}
**Usage:** {details.get('percent', 0):.0f}%

Budget limit approaching. Consider reducing usage.
"""
        return send_teams_message(message, "warning")

    elif alert_type == "error_spike":
        message = f"""**API Error Spike Detected**

**Time:** {timestamp}
**Errors in last hour:** {details.get('error_count', 0)}
**App:** {details.get('app', 'Unknown')}
**Last Error:** {details.get('last_error', 'Unknown')}

Please investigate API connectivity.
"""
        return send_teams_message(message, "error")

    else:
        return send_teams_message(f"Unknown alert: {alert_type}\n{json.dumps(details)}", "info")


if __name__ == "__main__":
    # Test notification
    print("Testing Teams notification...")
    send_teams_message("🧪 Test message from AI Usage Monitoring system", "info")
