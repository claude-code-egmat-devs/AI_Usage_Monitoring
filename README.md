# AI Usage Monitoring System

Centralized monitoring for all Anthropic API usage across VPS applications.

## Features

- **Centralized Logging** - All apps log to a shared directory
- **Daily Reports** - Automated summary sent to Teams at 11:30 PM IST
- **Real-time Alerts** - Warnings when thresholds exceeded
- **Budget Tracking** - Monitor monthly spend against limits
- **Multi-App Support** - Track usage per application

## Architecture

```
VPS Apps (Sales Forecasting, Sales Agent Form, etc.)
         |
         v
   Shared Logger Module (/home/.ai_monitoring/lib/)
         |
         v
   Centralized Logs (/home/.ai_monitoring/logs/)
         |
         +---> Daily Report (Cron @ 11:30 PM IST)
         |           |
         |           v
         |      Teams Notification
         |
         +---> Alert Monitor (Continuous)
                    |
                    v
               Teams Alerts (Warnings/Critical)
```

## Components

| Component | Description |
|-----------|-------------|
| `lib/ai_logger.py` | Shared logging module for all apps |
| `lib/teams_notifier.py` | Teams notification via Power Automate |
| `services/daily_report.py` | Generates and sends daily summaries |
| `services/alert_monitor.py` | Real-time threshold monitoring |
| `config/settings.json` | Thresholds, budgets, app registry |

## Installation on VPS

```bash
# Clone to VPS
cd /home
git clone https://github.com/brian-egmat/AI_Usage_Monitoring.git .ai_monitoring

# Create logs directory
mkdir -p /home/.ai_monitoring/logs

# Set up cron for daily reports (11:30 PM IST = 6:00 PM UTC)
crontab -e
# Add: 0 18 * * * /home/.ai_monitoring/venv/bin/python /home/.ai_monitoring/services/daily_report.py
```

## Usage in Apps

```python
# In your app's api.py or main module
import sys
sys.path.insert(0, '/home/.ai_monitoring/lib')
from ai_logger import log_ai_usage, generate_request_id

# Log usage
log_ai_usage(
    app_name="Sales_Forecasting",
    request_id=request_id,
    purpose="main_query",
    model="claude-sonnet-4-5-20250929",
    question=question,
    input_tokens=100,
    output_tokens=500,
    cost_usd=0.05
)
```

## Alert Types

| Alert | Trigger | Channel |
|-------|---------|---------|
| Warning | Daily cost > $5 | Teams |
| Critical | Daily cost > $10 | Teams |
| Budget Alert | Monthly spend > 80% of budget | Teams |
| Error Alert | >5 API errors in 1 hour | Teams |

## Configuration

Edit `config/settings.json`:

```json
{
  "thresholds": {
    "daily_warning_usd": 5.00,
    "daily_critical_usd": 10.00,
    "monthly_budget_usd": 100.00,
    "budget_alert_percent": 80
  },
  "teams": {
    "power_automate_url": "YOUR_URL",
    "chat_id": "YOUR_CHAT_ID",
    "agent_email": "your@email.com"
  }
}
```

## Daily Report Sample

```
📊 AI Usage Daily Report - 2026-01-12

📱 Apps Summary:
┌─────────────────────┬─────────┬──────────┬─────────┐
│ App                 │ Requests│ Tokens   │ Cost    │
├─────────────────────┼─────────┼──────────┼─────────┤
│ Sales_Forecasting   │ 45      │ 125,000  │ $3.25   │
│ Sales_Agent_Form    │ 12      │ 8,500    │ $0.45   │
└─────────────────────┴─────────┴──────────┴─────────┘

📈 Model Usage:
• claude-sonnet-4-5: 35 calls ($2.80)
• claude-haiku-4-5: 22 calls ($0.90)

💰 Budget Status:
• Today: $3.70
• Month-to-date: $45.20 / $100.00 (45%)

✅ Status: Normal
```

---

*Last Updated: 2026-01-12*
