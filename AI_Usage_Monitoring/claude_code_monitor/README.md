# Claude Code Usage Monitor

System-level monitoring for Claude Code CLI usage across multiple machines with MS Teams alerts.

## Features

- **Multi-machine tracking**: Monitor Claude Code usage from Windows, Linux, or any machine
- **Session-level details**: Track per-session tokens, costs, duration, and model usage
- **Automatic machine registration**: New machines are detected and registered automatically
- **Teams notifications**: Receive alerts for budget thresholds and daily summaries
- **Cost calculation**: Automatic cost calculation based on model pricing

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Local Windows  │     │      VPS        │
│  (~/.claude/)   │     │  (~/.claude/)   │
└────────┬────────┘     └────────┬────────┘
         │  usage_reporter       │  usage_reporter
         └───────────┬───────────┘
                     ▼
         ┌─────────────────────┐
         │   Aggregator (VPS)  │
         │     Port 8011       │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │   MS Teams Channel  │
         └─────────────────────┘
```

## Quick Start

### 1. Clone and Setup

```bash
# On VPS
cd /home
git clone <repo-url> claude-code-monitor
cd claude-code-monitor
./setup_linux.sh

# On Windows
cd claude_code_monitor
.\setup_windows.ps1
```

### 2. Configure

Copy `.env.example` to `.env` and configure:

```bash
cp config/.env.example config/.env
# Edit config/.env with your Power Automate URL and Teams settings
```

### 3. Run

**On VPS (Aggregator):**
```bash
# Start the aggregator service
./venv/bin/python services/aggregator_service.py

# Or with gunicorn for production
./venv/bin/gunicorn -w 2 -b 0.0.0.0:8011 services.aggregator_service:app
```

**On each machine (Reporter):**
```bash
# Test run (dry-run)
python services/usage_reporter.py --dry-run

# Actual run
python services/usage_reporter.py --aggregator-url http://your-vps:8011
```

## Components

### Library (`lib/`)

- `claude_usage_reader.py` - Reads Claude Code's local data from `~/.claude/`
- `cost_calculator.py` - Calculates costs based on token usage and model pricing
- `teams_notifier.py` - Sends notifications to Teams via Power Automate

### Services (`services/`)

- `usage_reporter.py` - Runs on each machine, collects and sends usage data
- `aggregator_service.py` - Central Flask service that receives reports and triggers alerts
- `daily_report.py` - Generates and sends daily summary reports

## Configuration

Edit `config/config.json`:

```json
{
  "thresholds": {
    "daily_warning_usd": 35,
    "daily_critical_usd": 45,
    "daily_limit_usd": 50
  },
  "teams": {
    "power_automate_url": "YOUR_URL",
    "chat_id": "YOUR_CHAT_ID"
  }
}
```

## Data Tracked Per Session

| Field | Description |
|-------|-------------|
| session_id | Unique session identifier |
| hostname | Machine hostname |
| model | Model used (opus, sonnet, haiku) |
| thinking_enabled | Extended thinking used |
| duration_hours | Session duration |
| input_tokens | Total input tokens |
| output_tokens | Total output tokens |
| cache_read_tokens | Cache read tokens |
| cache_write_tokens | Cache write tokens |
| cost_usd | Calculated cost |

## Alert Types

| Alert | Trigger |
|-------|---------|
| Daily Warning | 70% of daily budget |
| Daily Critical | 90% of daily budget |
| New Machine | First report from new machine |
| Daily Report | Scheduled at 11:30 PM IST |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/register` | POST | Register new machine |
| `/report` | POST | Submit usage report |
| `/status` | GET | Get current status |
| `/machines` | GET | List registered machines |

## Cron Setup (VPS)

```cron
# Reporter every 4 hours
0 */4 * * * /home/claude-code-monitor/venv/bin/python /home/claude-code-monitor/services/usage_reporter.py

# Daily report at 11:30 PM IST (18:00 UTC)
0 18 * * * /home/claude-code-monitor/venv/bin/python /home/claude-code-monitor/services/daily_report.py --send
```

## License

Internal use only.
