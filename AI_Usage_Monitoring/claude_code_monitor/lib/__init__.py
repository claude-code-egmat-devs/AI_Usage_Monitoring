"""
Claude Code Monitor Library

Core modules for reading Claude Code usage data and calculating costs.
"""

from .claude_usage_reader import (
    get_claude_dir,
    get_todays_usage,
    get_todays_sessions,
    get_model_usage_totals,
    parse_stats_cache,
    get_daily_stats,
    parse_session_jsonl,
)

from .cost_calculator import (
    calculate_cost,
    calculate_session_cost,
    calculate_daily_cost,
    format_cost,
    format_tokens,
    CostBreakdown,
    MODEL_PRICING,
)

from .teams_notifier import (
    send_teams_message,
    send_new_machine_alert,
    send_threshold_alert,
    send_daily_report,
    send_error_alert,
)

__all__ = [
    # Reader
    'get_claude_dir',
    'get_todays_usage',
    'get_todays_sessions',
    'get_model_usage_totals',
    'parse_stats_cache',
    'get_daily_stats',
    'parse_session_jsonl',
    # Cost
    'calculate_cost',
    'calculate_session_cost',
    'calculate_daily_cost',
    'format_cost',
    'format_tokens',
    'CostBreakdown',
    'MODEL_PRICING',
    # Teams
    'send_teams_message',
    'send_new_machine_alert',
    'send_threshold_alert',
    'send_daily_report',
    'send_error_alert',
]
