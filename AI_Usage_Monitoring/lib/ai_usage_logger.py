#!/usr/bin/env python3
"""
AI Usage Logger v2
Universal logging module for tracking Anthropic API usage across all VPS applications.
Thread-safe with fallback to local logging if central location unavailable.

Deploy to: /home/.ai_monitoring/lib/ai_usage_logger.py

Usage:
    from ai_usage_logger import AIUsageLogger
    logger = AIUsageLogger(app_name="My_App")
    logger.log_call(
        model="claude-sonnet-4-5-20250929",
        input_tokens=1000,
        output_tokens=500,
        purpose="query_analysis"
    )
"""
import json
import os
import threading
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

# Thread lock for file writes
_write_lock = threading.Lock()

# Central log directory (VPS location)
CENTRAL_LOG_DIR = '/home/.ai_monitoring/logs'

# Local fallback (relative to calling app)
LOCAL_FALLBACK_DIR = './logs'

# Current model pricing per 1M tokens (as of Jan 2025)
MODEL_PRICING = {
    # Claude 3.5 Sonnet (latest)
    "claude-sonnet-4-5-20250929": {
        "input_per_million": 3.00,
        "output_per_million": 15.00,
        "cache_write_per_million": 3.75,
        "cache_read_per_million": 0.30
    },
    # Claude 3.5 Haiku (latest)
    "claude-haiku-4-5-20251001": {
        "input_per_million": 0.80,
        "output_per_million": 4.00,
        "cache_write_per_million": 1.00,
        "cache_read_per_million": 0.08
    },
    # Claude 3 Opus
    "claude-3-opus-20240229": {
        "input_per_million": 15.00,
        "output_per_million": 75.00,
        "cache_write_per_million": 18.75,
        "cache_read_per_million": 1.50
    },
    # Claude 3 Sonnet
    "claude-3-sonnet-20240229": {
        "input_per_million": 3.00,
        "output_per_million": 15.00,
        "cache_write_per_million": 3.75,
        "cache_read_per_million": 0.30
    },
    # Claude 3 Haiku
    "claude-3-haiku-20240307": {
        "input_per_million": 0.25,
        "output_per_million": 1.25,
        "cache_write_per_million": 0.30,
        "cache_read_per_million": 0.03
    },
    # Default fallback (use Sonnet pricing)
    "default": {
        "input_per_million": 3.00,
        "output_per_million": 15.00,
        "cache_write_per_million": 3.75,
        "cache_read_per_million": 0.30
    }
}


class AIUsageLogger:
    """
    Universal AI usage logger with automatic cost calculation and centralized logging.

    Features:
    - Thread-safe file writes
    - Automatic cost calculation with current model pricing
    - Writes to centralized JSONL logs
    - Fallback to local logging if central unavailable
    - Support for extended thinking tokens
    """

    def __init__(
        self,
        app_name: str,
        central_log_dir: str = CENTRAL_LOG_DIR,
        local_fallback_dir: Optional[str] = LOCAL_FALLBACK_DIR,
        custom_pricing: Optional[Dict[str, Dict[str, float]]] = None
    ):
        """
        Initialize the AI Usage Logger.

        Args:
            app_name: Name of the application (e.g., "Sales_Forecasting", "GMAT_Forum")
            central_log_dir: Central directory for logs (default: /home/.ai_monitoring/logs)
            local_fallback_dir: Local fallback directory if central unavailable
            custom_pricing: Override default pricing for specific models
        """
        self.app_name = app_name
        self.central_log_dir = central_log_dir
        self.local_fallback_dir = local_fallback_dir
        self.pricing = {**MODEL_PRICING}

        if custom_pricing:
            self.pricing.update(custom_pricing)

        # Try to create central log dir
        self._log_dir = self._setup_log_directory()

    def _setup_log_directory(self) -> str:
        """Set up logging directory with fallback."""
        # Try central first
        try:
            os.makedirs(self.central_log_dir, exist_ok=True)
            # Test write access
            test_file = os.path.join(self.central_log_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return self.central_log_dir
        except (OSError, PermissionError):
            pass

        # Fall back to local
        if self.local_fallback_dir:
            try:
                os.makedirs(self.local_fallback_dir, exist_ok=True)
                return self.local_fallback_dir
            except (OSError, PermissionError):
                pass

        # Last resort: current directory
        return '.'

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        thinking_tokens: int = 0
    ) -> float:
        """
        Calculate cost based on token usage.

        Args:
            model: Model name/ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cache_creation_tokens: Tokens written to prompt cache
            cache_read_tokens: Tokens read from prompt cache
            thinking_tokens: Extended thinking tokens (counted as output)

        Returns:
            Cost in USD
        """
        # Get pricing for model or use default
        pricing = self.pricing.get(model, self.pricing.get('default', MODEL_PRICING['default']))

        # Calculate cost components
        input_cost = (input_tokens / 1_000_000) * pricing['input_per_million']
        output_cost = (output_tokens / 1_000_000) * pricing['output_per_million']
        cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing['cache_write_per_million']
        cache_read_cost = (cache_read_tokens / 1_000_000) * pricing['cache_read_per_million']
        thinking_cost = (thinking_tokens / 1_000_000) * pricing['output_per_million']

        total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost + thinking_cost

        return round(total_cost, 6)

    @staticmethod
    def generate_request_id() -> str:
        """Generate a unique request ID."""
        return str(uuid.uuid4())[:8]

    def log_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        purpose: str = "api_call",
        request_id: Optional[str] = None,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        thinking_tokens: int = 0,
        thinking_enabled: bool = False,
        latency_ms: int = 0,
        success: bool = True,
        error: Optional[str] = None,
        question: Optional[str] = None,
        response_preview: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log an AI API call with automatic cost calculation.

        Args:
            model: Model name/ID used for the call
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            purpose: Purpose of the call (e.g., "query", "extraction", "analysis")
            request_id: Unique request ID (auto-generated if not provided)
            cache_creation_tokens: Tokens written to prompt cache
            cache_read_tokens: Tokens read from prompt cache
            thinking_tokens: Extended thinking tokens used
            thinking_enabled: Whether extended thinking was enabled
            latency_ms: Response latency in milliseconds
            success: Whether the call succeeded
            error: Error message if call failed
            question: User's question/input (truncated to 500 chars)
            response_preview: Preview of response (truncated to 200 chars)
            metadata: Additional custom metadata

        Returns:
            The log entry dict that was written
        """
        if request_id is None:
            request_id = self.generate_request_id()

        # Calculate cost
        cost = self.calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            thinking_tokens=thinking_tokens
        )

        # Build log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "app_name": self.app_name,
            "request_id": request_id,
            "purpose": purpose,
            "model": model,
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
            "thinking_enabled": thinking_enabled
        }

        # Add optional fields
        if question:
            log_entry["question"] = question[:500]
        if response_preview:
            log_entry["response_preview"] = response_preview[:200]
        if metadata:
            log_entry["metadata"] = metadata

        # Write to log files
        self._write_log_entry(log_entry)

        return log_entry

    def _write_log_entry(self, entry: Dict[str, Any]) -> None:
        """Thread-safe write to log files."""
        with _write_lock:
            # Write to app-specific log
            app_log_file = os.path.join(self._log_dir, f"{self.app_name}.jsonl")
            self._append_to_file(app_log_file, entry)

            # Write to combined log (only if using central location)
            if self._log_dir == self.central_log_dir:
                combined_file = os.path.join(self._log_dir, "all_apps.jsonl")
                self._append_to_file(combined_file, entry)

    def _append_to_file(self, filepath: str, entry: Dict[str, Any]) -> None:
        """Append a JSON entry to a file."""
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[AIUsageLogger] Failed to write to {filepath}: {e}")

    def log_from_response(
        self,
        response,
        purpose: str = "api_call",
        request_id: Optional[str] = None,
        latency_ms: int = 0,
        question: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log usage directly from an Anthropic API response object.

        Args:
            response: The anthropic.types.Message response object
            purpose: Purpose of the call
            request_id: Unique request ID
            latency_ms: Response latency
            question: User's question/input
            metadata: Additional metadata

        Returns:
            The log entry dict
        """
        usage = response.usage

        # Extract response text for preview
        response_preview = None
        if response.content:
            for block in response.content:
                if hasattr(block, 'text'):
                    response_preview = block.text[:200]
                    break

        # Check for thinking tokens
        thinking_tokens = 0
        thinking_enabled = False
        if hasattr(usage, 'thinking_tokens'):
            thinking_tokens = usage.thinking_tokens or 0
            thinking_enabled = thinking_tokens > 0

        return self.log_call(
            model=response.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_creation_tokens=getattr(usage, 'cache_creation_input_tokens', 0) or 0,
            cache_read_tokens=getattr(usage, 'cache_read_input_tokens', 0) or 0,
            thinking_tokens=thinking_tokens,
            thinking_enabled=thinking_enabled,
            purpose=purpose,
            request_id=request_id,
            latency_ms=latency_ms,
            success=True,
            question=question,
            response_preview=response_preview,
            metadata=metadata
        )

    def log_error(
        self,
        error: str,
        model: str = "unknown",
        purpose: str = "api_call",
        request_id: Optional[str] = None,
        question: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log a failed API call.

        Args:
            error: Error message
            model: Model that was being called
            purpose: Purpose of the call
            request_id: Unique request ID
            question: User's question/input
            metadata: Additional metadata

        Returns:
            The log entry dict
        """
        return self.log_call(
            model=model,
            input_tokens=0,
            output_tokens=0,
            purpose=purpose,
            request_id=request_id,
            success=False,
            error=str(error),
            question=question,
            metadata=metadata
        )

    def get_today_stats(self) -> Dict[str, Any]:
        """Get usage statistics for today."""
        return self.get_stats_for_date(datetime.now())

    def get_stats_for_date(self, date: datetime) -> Dict[str, Any]:
        """Get usage statistics for a specific date."""
        date_str = date.strftime('%Y-%m-%d')
        log_file = os.path.join(self._log_dir, f"{self.app_name}.jsonl")

        stats = {
            'date': date_str,
            'requests': 0,
            'total_cost': 0.0,
            'total_tokens': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'errors': 0,
            'models': {}
        }

        if not os.path.exists(log_file):
            return stats

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if not entry.get('timestamp', '').startswith(date_str):
                            continue

                        stats['requests'] += 1
                        stats['total_cost'] += entry.get('cost_usd', 0) or 0

                        tokens = entry.get('tokens', {})
                        stats['input_tokens'] += tokens.get('input', 0)
                        stats['output_tokens'] += tokens.get('output', 0)
                        stats['total_tokens'] += tokens.get('input', 0) + tokens.get('output', 0)

                        if not entry.get('success', True):
                            stats['errors'] += 1

                        model = entry.get('model', 'unknown')
                        if model not in stats['models']:
                            stats['models'][model] = {'calls': 0, 'cost': 0.0}
                        stats['models'][model]['calls'] += 1
                        stats['models'][model]['cost'] += entry.get('cost_usd', 0) or 0

                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[AIUsageLogger] Error reading stats: {e}")

        return stats


# Convenience function for simple usage
def log_ai_usage(
    app_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    **kwargs
) -> Dict[str, Any]:
    """
    Simple function to log AI usage without creating a logger instance.

    Args:
        app_name: Name of the application
        model: Model name/ID
        input_tokens: Input token count
        output_tokens: Output token count
        **kwargs: Additional arguments passed to log_call()

    Returns:
        The log entry dict
    """
    logger = AIUsageLogger(app_name=app_name)
    return logger.log_call(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        **kwargs
    )


if __name__ == "__main__":
    # Example usage
    print("AI Usage Logger v2 - Example Usage")
    print("=" * 50)

    # Create logger
    logger = AIUsageLogger(app_name="Example_App")

    # Log a successful call
    entry = logger.log_call(
        model="claude-sonnet-4-5-20250929",
        input_tokens=1500,
        output_tokens=500,
        purpose="test_query",
        question="What is the capital of France?",
        response_preview="The capital of France is Paris...",
        latency_ms=1200
    )

    print(f"Logged entry:")
    print(json.dumps(entry, indent=2))

    # Get today's stats
    stats = logger.get_today_stats()
    print(f"\nToday's stats:")
    print(json.dumps(stats, indent=2))
