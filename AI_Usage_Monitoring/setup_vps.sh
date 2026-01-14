#!/bin/bash
# Setup script for AI Usage Monitoring on VPS
# Run this after cloning the repo to /home/.ai_monitoring

set -e

echo "Setting up AI Usage Monitoring..."

# Create directories
mkdir -p /home/.ai_monitoring/logs
mkdir -p /home/.ai_monitoring/venv

# Create virtual environment
python3 -m venv /home/.ai_monitoring/venv

# Install requirements
/home/.ai_monitoring/venv/bin/pip install -r /home/.ai_monitoring/requirements.txt

# Set permissions
chmod +x /home/.ai_monitoring/services/*.py

# Add cron jobs
echo "Adding cron jobs..."

# Daily report at 11:30 PM IST (6:00 PM UTC)
(crontab -l 2>/dev/null | grep -v "daily_report.py"; echo "0 18 * * * /home/.ai_monitoring/venv/bin/python /home/.ai_monitoring/services/daily_report.py >> /home/.ai_monitoring/logs/cron.log 2>&1") | crontab -

# Alert monitor every hour
(crontab -l 2>/dev/null | grep -v "alert_monitor.py"; echo "0 * * * * /home/.ai_monitoring/venv/bin/python /home/.ai_monitoring/services/alert_monitor.py >> /home/.ai_monitoring/logs/cron.log 2>&1") | crontab -

echo "Cron jobs added:"
crontab -l | grep ai_monitoring

echo ""
echo "Setup complete!"
echo ""
echo "To test notifications, run:"
echo "  /home/.ai_monitoring/venv/bin/python /home/.ai_monitoring/lib/teams_notifier.py"
echo ""
echo "To generate a report now, run:"
echo "  /home/.ai_monitoring/venv/bin/python /home/.ai_monitoring/services/daily_report.py"
