#!/usr/bin/env python3
"""
Log Adapters Module
Adapters to read AI usage logs from different formats and sources.

Deploy to: /home/.ai_monitoring/lib/log_adapters.py

Supported formats:
1. JSONL - Standard single-line JSON per entry (default)
2. DailyRotating - Daily files with pattern like ai_requests_2025-01-14.jsonl
3. Supabase - Query from Supabase database tables
4. PythonLogger - Extract from Python logger output files
"""
import json
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Generator
from glob import glob


class BaseLogAdapter(ABC):
    """Base class for all log adapters."""

    def __init__(self, app_name: str, config: Dict[str, Any]):
        """
        Initialize adapter.

        Args:
            app_name: Name of the application
            config: Configuration dict for this app from settings.json
        """
        self.app_name = app_name
        self.config = config

    @abstractmethod
    def read_entries(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Read log entries within a date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of log entry dicts
        """
        pass

    def get_entries_for_date(self, date: datetime) -> List[Dict[str, Any]]:
        """Get entries for a specific date."""
        return self.read_entries(start_date=date, end_date=date)

    def get_entries_for_today(self) -> List[Dict[str, Any]]:
        """Get entries for today."""
        return self.get_entries_for_date(datetime.now())

    def get_entries_for_month(self, year: int, month: int) -> List[Dict[str, Any]]:
        """Get entries for a specific month."""
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(year, month + 1, 1) - timedelta(days=1)
        return self.read_entries(start_date=start, end_date=end)


class JSONLAdapter(BaseLogAdapter):
    """
    Adapter for standard JSONL files (single JSON object per line).
    This is the default format used by the shared logger.
    """

    def read_entries(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Read entries from JSONL file."""
        log_file = self.config.get('log_file')
        if not log_file:
            return []

        if not os.path.exists(log_file):
            return []

        entries = []
        start_str = start_date.strftime('%Y-%m-%d') if start_date else None
        end_str = end_date.strftime('%Y-%m-%d') if end_date else None

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        timestamp = entry.get('timestamp', '')
                        date_part = timestamp[:10] if len(timestamp) >= 10 else ''

                        # Filter by date range
                        if start_str and date_part < start_str:
                            continue
                        if end_str and date_part > end_str:
                            continue

                        # Add app_name if not present
                        if 'app_name' not in entry:
                            entry['app_name'] = self.app_name

                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[JSONLAdapter] Error reading {log_file}: {e}")

        return entries


class DailyRotatingAdapter(BaseLogAdapter):
    """
    Adapter for daily rotating log files.
    Handles files like: ai_requests_2025-01-14.jsonl, ai_usage_20250114.jsonl, etc.
    Supports both JSONL format and multi-line JSON separated by '---'.
    """

    def _get_log_files_for_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[str]:
        """Get list of log files that fall within the date range."""
        log_dir = self.config.get('log_dir')
        file_pattern = self.config.get('file_pattern', 'ai_requests_*.jsonl')

        if not log_dir or not os.path.exists(log_dir):
            return []

        # Get all matching files
        pattern_path = os.path.join(log_dir, file_pattern)
        all_files = glob(pattern_path)

        if not all_files:
            return []

        # Extract date from filename and filter
        result_files = []
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # 2025-01-14
            r'(\d{8})',              # 20250114
        ]

        for filepath in all_files:
            filename = os.path.basename(filepath)

            # Try to extract date from filename
            file_date = None
            for pattern in date_patterns:
                match = re.search(pattern, filename)
                if match:
                    date_str = match.group(1)
                    try:
                        if '-' in date_str:
                            file_date = datetime.strptime(date_str, '%Y-%m-%d')
                        else:
                            file_date = datetime.strptime(date_str, '%Y%m%d')
                        break
                    except ValueError:
                        continue

            # If we couldn't extract date, include the file anyway
            if file_date is None:
                result_files.append(filepath)
                continue

            # Filter by date range
            if start_date and file_date.date() < start_date.date():
                continue
            if end_date and file_date.date() > end_date.date():
                continue

            result_files.append(filepath)

        return sorted(result_files)

    def _normalize_entry(self, raw_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize entry to standard format."""
        # Handle token_usage vs tokens field naming
        token_usage = raw_entry.get('token_usage', raw_entry.get('tokens', {}))
        if isinstance(token_usage, dict):
            tokens = {
                'input': token_usage.get('input_tokens', token_usage.get('input', 0)) or 0,
                'output': token_usage.get('output_tokens', token_usage.get('output', 0)) or 0,
                'cache_creation': token_usage.get('cache_creation_tokens', token_usage.get('cache_creation', 0)) or 0,
                'cache_read': token_usage.get('cache_read_tokens', token_usage.get('cache_read', 0)) or 0,
                'thinking': token_usage.get('thinking_tokens', token_usage.get('thinking', 0)) or 0
            }
        else:
            tokens = {'input': 0, 'output': 0, 'cache_creation': 0, 'cache_read': 0, 'thinking': 0}

        # Calculate cost if not present
        cost = raw_entry.get('cost_usd', 0)
        if not cost:
            # Use default Sonnet pricing
            cost = (
                (tokens['input'] / 1_000_000) * 3.00 +
                (tokens['output'] / 1_000_000) * 15.00
            )

        return {
            'app_name': raw_entry.get('app_name', self.app_name),
            'timestamp': raw_entry.get('timestamp', ''),
            'model': raw_entry.get('model', 'unknown'),
            'tokens': tokens,
            'cost_usd': round(cost, 6),
            'purpose': raw_entry.get('request_type', raw_entry.get('purpose', 'unknown')),
            'success': raw_entry.get('success', True),
            'thinking_enabled': raw_entry.get('thinking_enabled', False)
        }

    def read_entries(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Read entries from daily rotating files."""
        files = self._get_log_files_for_range(start_date, end_date)
        entries = []

        start_str = start_date.strftime('%Y-%m-%d') if start_date else None
        end_str = end_date.strftime('%Y-%m-%d') if end_date else None

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check if file uses '---' as separator (multi-line JSON)
                if '\n---\n' in content or content.strip().startswith('{'):
                    # Split by separator
                    chunks = content.split('\n---\n') if '\n---\n' in content else [content]

                    for chunk in chunks:
                        chunk = chunk.strip()
                        if not chunk:
                            continue

                        try:
                            raw_entry = json.loads(chunk)
                            entry = self._normalize_entry(raw_entry)

                            timestamp = entry.get('timestamp', '')
                            date_part = timestamp[:10] if len(timestamp) >= 10 else ''

                            # Filter by exact date if needed
                            if start_str and date_part and date_part < start_str:
                                continue
                            if end_str and date_part and date_part > end_str:
                                continue

                            entries.append(entry)
                        except json.JSONDecodeError as e:
                            # Skip malformed entries
                            continue
                else:
                    # Try JSONL format (one JSON per line)
                    for line in content.split('\n'):
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            raw_entry = json.loads(line)
                            entry = self._normalize_entry(raw_entry)

                            timestamp = entry.get('timestamp', '')
                            date_part = timestamp[:10] if len(timestamp) >= 10 else ''

                            if start_str and date_part and date_part < start_str:
                                continue
                            if end_str and date_part and date_part > end_str:
                                continue

                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue

            except Exception as e:
                print(f"[DailyRotatingAdapter] Error reading {filepath}: {e}")

        return entries


class SupabaseAdapter(BaseLogAdapter):
    """
    Adapter for reading logs from Supabase database.
    Requires supabase-py to be installed.
    """

    def __init__(self, app_name: str, config: Dict[str, Any]):
        super().__init__(app_name, config)
        self._client = None

    def _get_client(self):
        """Get or create Supabase client."""
        if self._client is not None:
            return self._client

        try:
            from supabase import create_client, Client

            url = self.config.get('supabase_url') or os.environ.get('SUPABASE_URL')
            key = self.config.get('supabase_key') or os.environ.get('SUPABASE_KEY')

            if not url or not key:
                print("[SupabaseAdapter] Missing Supabase URL or key")
                return None

            self._client = create_client(url, key)
            return self._client
        except ImportError:
            print("[SupabaseAdapter] supabase-py not installed")
            return None
        except Exception as e:
            print(f"[SupabaseAdapter] Error creating client: {e}")
            return None

    def read_entries(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Read entries from Supabase table."""
        client = self._get_client()
        if not client:
            return []

        table = self.config.get('table', 'llm_token_usage')
        timestamp_column = self.config.get('timestamp_column', 'created_at')

        try:
            query = client.table(table).select('*')

            if start_date:
                query = query.gte(timestamp_column, start_date.isoformat())
            if end_date:
                # Add one day to include the full end date
                end_plus = end_date + timedelta(days=1)
                query = query.lt(timestamp_column, end_plus.isoformat())

            result = query.execute()
            entries = []

            # Map Supabase columns to standard format
            column_mapping = self.config.get('column_mapping', {
                'timestamp': 'created_at',
                'model': 'model',
                'input_tokens': 'input_tokens',
                'output_tokens': 'output_tokens',
                'cost_usd': 'cost_usd',
                'purpose': 'purpose'
            })

            for row in result.data:
                entry = {
                    'app_name': self.app_name,
                    'timestamp': row.get(column_mapping.get('timestamp', 'created_at'), ''),
                    'model': row.get(column_mapping.get('model', 'model'), 'unknown'),
                    'tokens': {
                        'input': row.get(column_mapping.get('input_tokens', 'input_tokens'), 0) or 0,
                        'output': row.get(column_mapping.get('output_tokens', 'output_tokens'), 0) or 0,
                        'cache_creation': row.get('cache_creation_tokens', 0) or 0,
                        'cache_read': row.get('cache_read_tokens', 0) or 0
                    },
                    'cost_usd': row.get(column_mapping.get('cost_usd', 'cost_usd'), 0) or 0,
                    'purpose': row.get(column_mapping.get('purpose', 'purpose'), 'unknown'),
                    'success': row.get('success', True)
                }
                entries.append(entry)

            return entries

        except Exception as e:
            print(f"[SupabaseAdapter] Error querying Supabase: {e}")
            return []


class PythonLoggerAdapter(BaseLogAdapter):
    """
    Adapter for extracting AI usage from Python logger output files.
    Looks for specific patterns in log lines that contain token/cost info.
    """

    # Patterns to extract usage info from log lines
    PATTERNS = {
        'tokens': re.compile(r'tokens[:\s]+(\d+)', re.IGNORECASE),
        'input_tokens': re.compile(r'input[_\s]?tokens[:\s]+(\d+)', re.IGNORECASE),
        'output_tokens': re.compile(r'output[_\s]?tokens[:\s]+(\d+)', re.IGNORECASE),
        'cost': re.compile(r'cost[:\s]+\$?([\d.]+)', re.IGNORECASE),
        'model': re.compile(r'model[:\s]+([a-z0-9\-_]+)', re.IGNORECASE),
        'timestamp': re.compile(r'^(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})')
    }

    def read_entries(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Read and parse Python logger output for AI usage."""
        log_file = self.config.get('log_file')
        if not log_file or not os.path.exists(log_file):
            return []

        entries = []
        start_str = start_date.strftime('%Y-%m-%d') if start_date else None
        end_str = end_date.strftime('%Y-%m-%d') if end_date else None

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Look for lines that contain AI usage info
                    if not any(kw in line.lower() for kw in ['token', 'cost', 'claude', 'anthropic']):
                        continue

                    # Try to extract timestamp
                    timestamp_match = self.PATTERNS['timestamp'].search(line)
                    timestamp = timestamp_match.group(1) if timestamp_match else ''
                    date_part = timestamp[:10] if len(timestamp) >= 10 else ''

                    # Filter by date
                    if start_str and date_part and date_part < start_str:
                        continue
                    if end_str and date_part and date_part > end_str:
                        continue

                    # Extract other fields
                    entry = {
                        'app_name': self.app_name,
                        'timestamp': timestamp,
                        'tokens': {
                            'input': 0,
                            'output': 0,
                            'cache_creation': 0,
                            'cache_read': 0
                        },
                        'cost_usd': 0.0,
                        'model': 'unknown',
                        'success': True
                    }

                    # Try input/output tokens first
                    input_match = self.PATTERNS['input_tokens'].search(line)
                    if input_match:
                        entry['tokens']['input'] = int(input_match.group(1))

                    output_match = self.PATTERNS['output_tokens'].search(line)
                    if output_match:
                        entry['tokens']['output'] = int(output_match.group(1))

                    # Fall back to generic tokens
                    if entry['tokens']['input'] == 0 and entry['tokens']['output'] == 0:
                        tokens_match = self.PATTERNS['tokens'].search(line)
                        if tokens_match:
                            total = int(tokens_match.group(1))
                            entry['tokens']['input'] = total // 2
                            entry['tokens']['output'] = total - entry['tokens']['input']

                    cost_match = self.PATTERNS['cost'].search(line)
                    if cost_match:
                        entry['cost_usd'] = float(cost_match.group(1))

                    model_match = self.PATTERNS['model'].search(line)
                    if model_match:
                        entry['model'] = model_match.group(1)

                    # Only add if we found some useful data
                    if entry['tokens']['input'] > 0 or entry['tokens']['output'] > 0 or entry['cost_usd'] > 0:
                        entries.append(entry)

        except Exception as e:
            print(f"[PythonLoggerAdapter] Error reading {log_file}: {e}")

        return entries


# Adapter registry
ADAPTER_TYPES = {
    'jsonl': JSONLAdapter,
    'daily_rotating': DailyRotatingAdapter,
    'supabase': SupabaseAdapter,
    'python_logger': PythonLoggerAdapter
}


def get_adapter(app_name: str, config: Dict[str, Any]) -> BaseLogAdapter:
    """
    Factory function to get the appropriate adapter for an app.

    Args:
        app_name: Name of the application
        config: App configuration from settings.json

    Returns:
        Appropriate adapter instance
    """
    adapter_type = config.get('adapter_type', 'jsonl')
    adapter_class = ADAPTER_TYPES.get(adapter_type, JSONLAdapter)
    return adapter_class(app_name, config)


def read_all_apps(
    settings: Dict[str, Any],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Read entries from all configured apps.

    Args:
        settings: Full settings.json content
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Dict mapping app names to their entries
    """
    apps_config = settings.get('apps', {})
    all_entries = {}

    for app_name, app_config in apps_config.items():
        adapter = get_adapter(app_name, app_config)
        entries = adapter.read_entries(start_date=start_date, end_date=end_date)
        all_entries[app_name] = entries

    return all_entries


if __name__ == "__main__":
    print("Log Adapters Module - Available Adapters:")
    print("=" * 50)
    for name, cls in ADAPTER_TYPES.items():
        print(f"  - {name}: {cls.__doc__.split(chr(10))[1].strip() if cls.__doc__ else 'No description'}")
