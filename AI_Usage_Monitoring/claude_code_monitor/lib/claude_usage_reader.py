"""
Claude Code Usage Reader

Reads Claude Code's local usage data from ~/.claude/ directory.
Parses stats-cache.json for aggregates and session JSONL files for detailed metrics.
"""

import json
import os
import glob
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any


def get_claude_dir() -> Path:
    """Get the Claude Code data directory path."""
    if os.name == 'nt':  # Windows
        return Path(os.path.expanduser("~/.claude"))
    else:  # Linux/Mac
        return Path.home() / ".claude"


def parse_stats_cache(claude_dir: Path) -> Optional[Dict]:
    """Parse the stats-cache.json file for aggregated statistics."""
    stats_file = claude_dir / "stats-cache.json"
    if not stats_file.exists():
        return None

    with open(stats_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_daily_stats(stats_cache: Dict, target_date: date) -> Dict:
    """Extract daily statistics for a specific date."""
    date_str = target_date.isoformat()

    result = {
        'date': date_str,
        'message_count': 0,
        'session_count': 0,
        'tool_call_count': 0,
        'tokens_by_model': {}
    }

    # Find daily activity
    for activity in stats_cache.get('dailyActivity', []):
        if activity.get('date') == date_str:
            result['message_count'] = activity.get('messageCount', 0)
            result['session_count'] = activity.get('sessionCount', 0)
            result['tool_call_count'] = activity.get('toolCallCount', 0)
            break

    # Find daily model tokens
    for tokens in stats_cache.get('dailyModelTokens', []):
        if tokens.get('date') == date_str:
            result['tokens_by_model'] = tokens.get('tokensByModel', {})
            break

    return result


def parse_session_jsonl(session_file: Path) -> Dict:
    """
    Parse a session JSONL file to extract detailed usage metrics.

    Returns session details including:
    - session_id
    - model
    - timestamps (start/end)
    - token usage (input, output, cache)
    - request count
    - tool call count
    """
    session_id = session_file.stem  # Filename without extension

    # Skip agent files
    if session_id.startswith('agent-'):
        return None

    session_data = {
        'session_id': session_id,
        'model': None,
        'project_path': None,
        'start_time': None,
        'end_time': None,
        'input_tokens': 0,
        'output_tokens': 0,
        'cache_read_tokens': 0,
        'cache_write_tokens': 0,
        'request_count': 0,
        'tool_call_count': 0,
        'messages': []
    }

    timestamps = []
    models_used = set()

    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Skip summary entries
            if entry.get('type') == 'summary':
                continue

            # Extract model
            if 'message' in entry and isinstance(entry['message'], dict):
                msg = entry['message']
                if 'model' in msg:
                    models_used.add(msg['model'])

                # Extract usage from message
                if 'usage' in msg:
                    usage = msg['usage']
                    session_data['input_tokens'] += usage.get('input_tokens', 0)
                    session_data['output_tokens'] += usage.get('output_tokens', 0)
                    session_data['cache_read_tokens'] += usage.get('cache_read_input_tokens', 0)
                    session_data['cache_write_tokens'] += usage.get('cache_creation_input_tokens', 0)
                    session_data['request_count'] += 1

            # Extract project path
            if 'cwd' in entry and not session_data['project_path']:
                session_data['project_path'] = entry['cwd']

            # Extract timestamp (handles both ISO string and millisecond formats)
            if 'timestamp' in entry:
                try:
                    ts_val = entry['timestamp']
                    if isinstance(ts_val, str):
                        # ISO format: "2026-01-14T07:46:06.958Z"
                        ts = datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                    else:
                        # Millisecond timestamp
                        ts = datetime.fromtimestamp(ts_val / 1000, tz=timezone.utc)
                    timestamps.append(ts)
                except (ValueError, TypeError):
                    pass

            # Count tool calls
            if 'message' in entry and isinstance(entry['message'], dict):
                content = entry['message'].get('content', [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'tool_use':
                            session_data['tool_call_count'] += 1

    # Set model (use primary model - opus > sonnet > haiku)
    if models_used:
        for model_priority in ['opus', 'sonnet', 'haiku']:
            for model in models_used:
                if model_priority in model.lower():
                    session_data['model'] = model
                    break
            if session_data['model']:
                break
        if not session_data['model']:
            session_data['model'] = list(models_used)[0]

    # Set timestamps
    if timestamps:
        session_data['start_time'] = min(timestamps).isoformat()
        session_data['end_time'] = max(timestamps).isoformat()

        # Calculate duration in hours
        duration = (max(timestamps) - min(timestamps)).total_seconds() / 3600
        session_data['duration_hours'] = round(duration, 2)

    # Detect thinking mode (high output/input ratio suggests thinking)
    if session_data['input_tokens'] > 0:
        ratio = session_data['output_tokens'] / session_data['input_tokens']
        session_data['thinking_enabled'] = ratio > 5  # Heuristic
    else:
        session_data['thinking_enabled'] = False

    return session_data if session_data['request_count'] > 0 else None


def get_sessions_for_date(claude_dir: Path, target_date: date) -> List[Dict]:
    """Get all sessions that were active on a specific date."""
    sessions = []
    projects_dir = claude_dir / "projects"

    if not projects_dir.exists():
        return sessions

    # Scan all project directories
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Find all session JSONL files
        for session_file in project_dir.glob("*.jsonl"):
            # Check file modification date
            file_mtime = datetime.fromtimestamp(session_file.stat().st_mtime)

            # Include if modified on or after target date (rough filter)
            if file_mtime.date() >= target_date:
                session_data = parse_session_jsonl(session_file)
                if session_data:
                    # Filter by actual session timestamps
                    if session_data.get('start_time'):
                        session_date = datetime.fromisoformat(
                            session_data['start_time'].replace('Z', '+00:00')
                        ).date()
                        if session_date == target_date:
                            sessions.append(session_data)

    return sessions


def get_todays_sessions(claude_dir: Path = None) -> List[Dict]:
    """Get all sessions active today."""
    if claude_dir is None:
        claude_dir = get_claude_dir()
    return get_sessions_for_date(claude_dir, date.today())


def get_todays_usage(claude_dir: Path = None) -> Dict:
    """
    Get comprehensive usage data for today.

    Returns:
        Dict with daily stats, sessions list, and totals
    """
    if claude_dir is None:
        claude_dir = get_claude_dir()

    today = date.today()

    # Get aggregated stats
    stats_cache = parse_stats_cache(claude_dir)
    daily_stats = get_daily_stats(stats_cache, today) if stats_cache else {}

    # Get detailed sessions
    sessions = get_sessions_for_date(claude_dir, today)

    # Calculate totals from sessions
    totals = {
        'total_input_tokens': sum(s.get('input_tokens', 0) for s in sessions),
        'total_output_tokens': sum(s.get('output_tokens', 0) for s in sessions),
        'total_cache_read_tokens': sum(s.get('cache_read_tokens', 0) for s in sessions),
        'total_cache_write_tokens': sum(s.get('cache_write_tokens', 0) for s in sessions),
        'total_requests': sum(s.get('request_count', 0) for s in sessions),
        'total_tool_calls': sum(s.get('tool_call_count', 0) for s in sessions),
        'session_count': len(sessions)
    }

    # Group by model
    models = {}
    for session in sessions:
        model = session.get('model', 'unknown')
        if model not in models:
            models[model] = {
                'input_tokens': 0,
                'output_tokens': 0,
                'cache_read_tokens': 0,
                'cache_write_tokens': 0,
                'sessions': 0
            }
        models[model]['input_tokens'] += session.get('input_tokens', 0)
        models[model]['output_tokens'] += session.get('output_tokens', 0)
        models[model]['cache_read_tokens'] += session.get('cache_read_tokens', 0)
        models[model]['cache_write_tokens'] += session.get('cache_write_tokens', 0)
        models[model]['sessions'] += 1

    return {
        'date': today.isoformat(),
        'daily_stats': daily_stats,
        'sessions': sessions,
        'totals': totals,
        'by_model': models
    }


def get_model_usage_totals(claude_dir: Path = None) -> Dict:
    """Get total model usage from stats-cache.json."""
    if claude_dir is None:
        claude_dir = get_claude_dir()

    stats_cache = parse_stats_cache(claude_dir)
    if not stats_cache:
        return {}

    return stats_cache.get('modelUsage', {})


# CLI for testing
if __name__ == "__main__":
    import pprint

    print("=" * 60)
    print("Claude Code Usage Reader - Test Run")
    print("=" * 60)

    claude_dir = get_claude_dir()
    print(f"\nClaude directory: {claude_dir}")
    print(f"Directory exists: {claude_dir.exists()}")

    print("\n--- Today's Usage ---")
    usage = get_todays_usage()

    print(f"\nDate: {usage['date']}")
    print(f"Sessions found: {len(usage['sessions'])}")

    print("\nTotals:")
    for key, value in usage['totals'].items():
        print(f"  {key}: {value:,}")

    print("\nBy Model:")
    for model, data in usage['by_model'].items():
        print(f"  {model}:")
        for key, value in data.items():
            print(f"    {key}: {value:,}")

    if usage['sessions']:
        print("\nSession Details:")
        for session in usage['sessions'][:3]:  # Show first 3
            print(f"\n  Session: {session['session_id'][:8]}...")
            print(f"    Model: {session.get('model', 'N/A')}")
            print(f"    Duration: {session.get('duration_hours', 0)} hrs")
            print(f"    Input tokens: {session.get('input_tokens', 0):,}")
            print(f"    Output tokens: {session.get('output_tokens', 0):,}")
            print(f"    Thinking: {session.get('thinking_enabled', False)}")
