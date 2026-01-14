#!/bin/bash
# Claude Code Monitor - Linux Setup Script
# Run this script to set up the monitor on a Linux/VPS machine

echo "============================================================"
echo "Claude Code Monitor - Linux Setup"
echo "============================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
echo -e "\nChecking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.9+"
    exit 1
fi
python3 --version

# Create virtual environment
VENV_PATH="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "\nCreating virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# Activate and install dependencies
echo -e "\nInstalling dependencies..."
"$VENV_PATH/bin/pip" install -r requirements.txt

# Check .env
if [ ! -f "$SCRIPT_DIR/config/.env" ]; then
    echo -e "\nWARNING: .env file not found"
    echo "Please copy config/.env.example to config/.env and configure it"
fi

# Test the usage reader
echo -e "\nTesting usage reader..."
"$VENV_PATH/bin/python" lib/claude_usage_reader.py

echo -e "\n============================================================"
echo "Setup Complete!"
echo "============================================================"

echo -e "\nTo run the reporter manually:"
echo "  ./venv/bin/python services/usage_reporter.py --dry-run"

echo -e "\nTo run the aggregator service:"
echo "  ./venv/bin/python services/aggregator_service.py"

echo -e "\nTo set up cron jobs:"
cat << 'CRON'

# Edit crontab with: crontab -e
# Add these lines:

# Run usage reporter every 4 hours
0 */4 * * * /home/claude-code-monitor/venv/bin/python /home/claude-code-monitor/services/usage_reporter.py >> /home/claude-code-monitor/logs/reporter.log 2>&1

# Send daily report at 11:30 PM IST (18:00 UTC)
0 18 * * * /home/claude-code-monitor/venv/bin/python /home/claude-code-monitor/services/daily_report.py --send >> /home/claude-code-monitor/logs/daily_report.log 2>&1

CRON

echo -e "\nTo run aggregator as a systemd service:"
cat << 'SYSTEMD'

# Create /etc/systemd/system/claude-code-monitor.service:

[Unit]
Description=Claude Code Monitor Aggregator
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/claude-code-monitor
ExecStart=/home/claude-code-monitor/venv/bin/gunicorn -w 2 -b 0.0.0.0:8011 services.aggregator_service:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Then run:
# sudo systemctl daemon-reload
# sudo systemctl enable claude-code-monitor
# sudo systemctl start claude-code-monitor

SYSTEMD
