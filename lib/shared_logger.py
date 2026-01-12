"""
Shared AI Usage Logger
Import this module in any app to log AI usage to centralized location
"""
import json
import os
from datetime import datetime
import uuid

# Central log directory
CENTRAL_LOG_DIR = '/home/.ai_monitoring/logs'

# Pricing per 1M tokens
PRICING = {
    "claude-sonnet-4-5-20250929": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30
    },
    "claude-haiku-4-5-20251001": {
        "input": 0.80,
        "output": 4.00,
        "cache_write": 1.00,
        "cache_read": 0.08
    }
}


def ensure_log_dir(log_dir=CENTRAL_LOG_DIR):
    """Ensure the logs directory exists"""
    os.makedirs(log_dir, exist_ok=True)


def calculate_cost(model, input_tokens, output_tokens, cache_creation_tokens=0, cache_read_tokens=0):
    """Calculate cost based on token usage"""
    pricing = PRICING.get(model, PRICING["claude-sonnet-4-5-20250929"])

    cost = (
        (input_tokens / 1_000_000) * pricing["input"] +
        (output_tokens / 1_000_000) * pricing["output"] +
        (cache_creation_tokens / 1_000_000) * pricing["cache_write"] +
        (cache_read_tokens / 1_000_000) * pricing["cache_read"]
    )

    return round(cost, 6)


def generate_request_id():
    """Generate a unique request ID"""
    return str(uuid.uuid4())[:8]


def log_ai_usage(
    app_name,
    request_id,
    purpose,
    model,
    question,
    input_tokens,
    output_tokens,
    cache_creation_tokens=0,
    cache_read_tokens=0,
    latency_ms=0,
    success=True,
    error=None,
    user_timestamp=None,
    date_extracted=None,
    thinking_enabled=False,
    thinking_tokens=0,
    response_preview=None,
    log_dir=CENTRAL_LOG_DIR
):
    """
    Log AI usage to centralized location

    Parameters:
    - app_name: Name of the application (e.g., "Sales_Forecasting")
    - request_id: Unique ID for the request
    - purpose: "date_extraction", "main_query", etc.
    - model: Model used
    - question: User's question
    - input_tokens: Input tokens used
    - output_tokens: Output tokens used
    - cache_creation_tokens: Tokens written to cache
    - cache_read_tokens: Tokens read from cache
    - latency_ms: Response time in milliseconds
    - success: Whether the call succeeded
    - error: Error message if any
    - user_timestamp: User's local timestamp
    - date_extracted: Date range extracted (if applicable)
    - thinking_enabled: Whether extended thinking was enabled
    - thinking_tokens: Tokens used for thinking
    - response_preview: First 200 chars of response
    - log_dir: Directory to write logs (default: central location)
    """
    ensure_log_dir(log_dir)

    cost = calculate_cost(model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)

    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "app_name": app_name,
        "request_id": request_id,
        "purpose": purpose,
        "model": model,
        "question": question[:500] if question else None,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "cache_creation": cache_creation_tokens,
            "cache_read": cache_read_tokens,
            "thinking": thinking_tokens
        },
        "cost_usd": cost,
        "latency_ms": latency_ms,
        "success": success,
        "error": error,
        "user_timestamp": user_timestamp,
        "date_extracted": date_extracted,
        "thinking_enabled": thinking_enabled,
        "response_preview": response_preview[:200] if response_preview else None
    }

    # Write to app-specific file in central location
    log_file = os.path.join(log_dir, f"{app_name}.jsonl")

    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        print(f"Failed to write AI usage log: {e}")

    # Also write to combined log
    combined_file = os.path.join(log_dir, "all_apps.jsonl")
    try:
        with open(combined_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        print(f"Failed to write combined log: {e}")

    return log_entry


# Convenience function to get daily stats for an app
def get_daily_stats(app_name, date=None, log_dir=CENTRAL_LOG_DIR):
    """Get usage stats for a specific app and date"""
    if date is None:
        date = datetime.now()

    date_str = date.strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f"{app_name}.jsonl")

    if not os.path.exists(log_file):
        return {'requests': 0, 'cost': 0, 'tokens': 0}

    stats = {'requests': 0, 'cost': 0.0, 'tokens': 0, 'errors': 0}

    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get('timestamp', '').startswith(date_str):
                    stats['requests'] += 1
                    stats['cost'] += entry.get('cost_usd', 0) or 0
                    tokens = entry.get('tokens', {})
                    stats['tokens'] += (
                        tokens.get('input', 0) +
                        tokens.get('output', 0)
                    )
                    if not entry.get('success', True):
                        stats['errors'] += 1
            except:
                continue

    return stats
