# AI Usage Monitoring - Integration Guide

This guide explains how to add AI usage tracking to your VPS applications.

## Quick Start

There are two ways to integrate with the monitoring system:

1. **Use the Shared Logger** (Recommended) - Your app writes logs using our module
2. **Configure an Adapter** - We read your existing logs in their native format

---

## Option 1: Using the Shared Logger (Recommended)

Best for new apps or apps being updated during maintenance.

### Step 1: Import the Logger

```python
from ai_usage_logger import AIUsageLogger

# Create logger instance
logger = AIUsageLogger(app_name="Your_App_Name")
```

### Step 2: Log API Calls

**Method A: Manual logging (simple)**
```python
# After receiving API response
logger.log_call(
    model="claude-sonnet-4-5-20250929",
    input_tokens=1500,
    output_tokens=500,
    purpose="query_analysis",
    question="User's question here",
    latency_ms=1200
)
```

**Method B: Log from Anthropic response (easiest)**
```python
import anthropic
import time

client = anthropic.Anthropic()
start = time.time()

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)

latency = int((time.time() - start) * 1000)

# Log directly from response object
logger.log_from_response(
    response=response,
    purpose="greeting",
    latency_ms=latency,
    question="Hello!"
)
```

**Method C: Log errors**
```python
try:
    response = client.messages.create(...)
except Exception as e:
    logger.log_error(
        error=str(e),
        model="claude-sonnet-4-5-20250929",
        purpose="query_analysis",
        question="User's question"
    )
    raise
```

### Step 3: Add to settings.json

After deploying the logger code, add your app to `/home/.ai_monitoring/config/settings.json`:

```json
{
  "apps": {
    "Your_App_Name": {
      "adapter_type": "jsonl",
      "log_file": "/home/.ai_monitoring/logs/Your_App_Name.jsonl",
      "description": "Description of your app"
    }
  }
}
```

---

## Option 2: Configure an Adapter (No Code Changes)

Best for apps that already log AI usage in some format.

### Available Adapters

| Adapter | Use Case | Required Config |
|---------|----------|-----------------|
| `jsonl` | Single JSONL file | `log_file` |
| `daily_rotating` | Daily log files | `log_dir`, `file_pattern` |
| `supabase` | Supabase database | `table`, credentials |
| `python_logger` | Python logger output | `log_file` |

### Adapter Configurations

#### JSONL Adapter (Default)
For apps writing one JSON object per line:

```json
{
  "apps": {
    "My_App": {
      "adapter_type": "jsonl",
      "log_file": "/path/to/ai_usage.jsonl",
      "description": "My application"
    }
  }
}
```

Expected log format:
```json
{"timestamp": "2025-01-14T10:30:00Z", "model": "claude-sonnet-4-5-20250929", "tokens": {"input": 1000, "output": 500}, "cost_usd": 0.012}
```

#### Daily Rotating Adapter
For apps creating daily log files:

```json
{
  "apps": {
    "My_App": {
      "adapter_type": "daily_rotating",
      "log_dir": "/path/to/logs",
      "file_pattern": "ai_requests_*.jsonl",
      "description": "My application with daily logs"
    }
  }
}
```

Supports patterns like:
- `ai_requests_2025-01-14.jsonl`
- `ai_usage_20250114.jsonl`

#### Supabase Adapter
For apps logging to Supabase:

```json
{
  "apps": {
    "My_App": {
      "adapter_type": "supabase",
      "table": "llm_token_usage",
      "timestamp_column": "created_at",
      "supabase_url": "https://xxx.supabase.co",
      "supabase_key": "your-anon-key",
      "column_mapping": {
        "timestamp": "created_at",
        "model": "model_name",
        "input_tokens": "prompt_tokens",
        "output_tokens": "completion_tokens",
        "cost_usd": "cost"
      },
      "description": "App using Supabase"
    }
  }
}
```

Or use environment variables:
- `SUPABASE_URL`
- `SUPABASE_KEY`

#### Python Logger Adapter
For apps using Python's logging module with AI info in logs:

```json
{
  "apps": {
    "My_App": {
      "adapter_type": "python_logger",
      "log_file": "/var/log/my_app/app.log",
      "description": "Legacy app with logger output"
    }
  }
}
```

This adapter searches for patterns like:
- `input_tokens: 1500`
- `output_tokens: 500`
- `cost: $0.012`
- `model: claude-sonnet-4-5-20250929`

---

## Log Entry Schema

All entries (regardless of adapter) should include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp |
| `model` | string | Yes | Model name/ID |
| `tokens.input` | int | Yes | Input token count |
| `tokens.output` | int | Yes | Output token count |
| `cost_usd` | float | No | Cost in USD (auto-calculated if missing) |
| `purpose` | string | No | Call purpose (e.g., "query", "extraction") |
| `success` | bool | No | Whether call succeeded (default: true) |
| `app_name` | string | No | Application name |
| `request_id` | string | No | Unique request identifier |

Optional fields:
- `tokens.cache_creation` - Prompt cache write tokens
- `tokens.cache_read` - Prompt cache read tokens
- `tokens.thinking` - Extended thinking tokens
- `latency_ms` - Response time in milliseconds
- `error` - Error message if failed
- `question` - User input (truncated to 500 chars)
- `response_preview` - Response preview (truncated to 200 chars)
- `metadata` - Custom metadata dict

---

## Model Pricing

Current pricing (per 1M tokens):

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| claude-sonnet-4-5-20250929 | $3.00 | $15.00 | $3.75 | $0.30 |
| claude-haiku-4-5-20251001 | $0.80 | $4.00 | $1.00 | $0.08 |
| claude-3-opus-20240229 | $15.00 | $75.00 | $18.75 | $1.50 |
| claude-3-haiku-20240307 | $0.25 | $1.25 | $0.30 | $0.03 |

---

## Testing Your Integration

### 1. Verify Log File
```bash
# Check if log file exists and has recent entries
tail -5 /home/.ai_monitoring/logs/Your_App.jsonl
```

### 2. Test with Preview
```bash
cd /home/.ai_monitoring
python services/daily_report_v2.py --preview
```

### 3. Check for Your App
Look for your app in the preview output. Verify:
- Correct request count
- Reasonable token counts
- Cost looks right

---

## Troubleshooting

### "App not showing in report"
1. Check settings.json has your app configured
2. Verify log file path is correct
3. Check log file has entries for today

### "Adapter error"
1. Check adapter_type matches your log format
2. For daily_rotating: verify file_pattern matches actual files
3. For Supabase: check credentials and table name

### "Zero tokens/cost"
1. Verify log entries have correct field names
2. Check timestamp format is ISO 8601
3. For adapters: check column_mapping if using non-standard names

### "Permission denied"
1. Ensure monitoring system user can read log files
2. For Supabase: check API key has read permissions

---

## Getting Help

For issues or questions:
1. Check this guide first
2. Review existing app configurations in settings.json
3. Test with `--preview` flag to debug
4. Check logs in `/home/.ai_monitoring/logs/`

---

## Appendix: Full Example

### Complete Integration Example

```python
# my_app/ai_client.py
import time
import anthropic
from ai_usage_logger import AIUsageLogger

# Initialize once at module level
logger = AIUsageLogger(app_name="My_App")
client = anthropic.Anthropic()

def query_claude(question: str, purpose: str = "user_query") -> str:
    """Query Claude and automatically log usage."""
    request_id = logger.generate_request_id()
    start_time = time.time()

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{"role": "user", "content": question}]
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Log successful call
        logger.log_from_response(
            response=response,
            purpose=purpose,
            request_id=request_id,
            latency_ms=latency_ms,
            question=question
        )

        return response.content[0].text

    except Exception as e:
        # Log failed call
        logger.log_error(
            error=str(e),
            model="claude-sonnet-4-5-20250929",
            purpose=purpose,
            request_id=request_id,
            question=question
        )
        raise
```

### Corresponding settings.json Entry

```json
{
  "apps": {
    "My_App": {
      "adapter_type": "jsonl",
      "log_file": "/home/.ai_monitoring/logs/My_App.jsonl",
      "description": "My Application - User queries"
    }
  }
}
```
