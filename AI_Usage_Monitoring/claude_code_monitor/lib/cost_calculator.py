"""
Cost Calculator for Claude Code Usage

Calculates costs based on token usage and model pricing.
Pricing is based on Anthropic's official API rates.
"""

from typing import Dict, Optional
from dataclasses import dataclass


# Pricing per million tokens (USD)
# Updated: January 2026
MODEL_PRICING = {
    # Claude Opus 4.5
    "claude-opus-4-5-20251101": {
        "input_per_million": 15.00,
        "output_per_million": 75.00,
        "cache_write_per_million": 18.75,  # 1.25x input
        "cache_read_per_million": 1.50,    # 0.1x input
    },
    # Claude Sonnet 4.5
    "claude-sonnet-4-5-20250929": {
        "input_per_million": 3.00,
        "output_per_million": 15.00,
        "cache_write_per_million": 3.75,
        "cache_read_per_million": 0.30,
    },
    # Claude Sonnet 4
    "claude-sonnet-4-20250514": {
        "input_per_million": 3.00,
        "output_per_million": 15.00,
        "cache_write_per_million": 3.75,
        "cache_read_per_million": 0.30,
    },
    # Claude Haiku 3.5
    "claude-haiku-3-5-20241022": {
        "input_per_million": 0.80,
        "output_per_million": 4.00,
        "cache_write_per_million": 1.00,
        "cache_read_per_million": 0.08,
    },
}

# Fallback pricing for unknown models (use sonnet rates)
DEFAULT_PRICING = {
    "input_per_million": 3.00,
    "output_per_million": 15.00,
    "cache_write_per_million": 3.75,
    "cache_read_per_million": 0.30,
}


@dataclass
class CostBreakdown:
    """Detailed cost breakdown."""
    input_cost: float
    output_cost: float
    cache_read_cost: float
    cache_write_cost: float
    total_cost: float
    model: str


def get_model_pricing(model: str) -> Dict:
    """Get pricing for a model, with fallback to default."""
    # Direct match
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]

    # Try partial match
    model_lower = model.lower()
    for known_model, pricing in MODEL_PRICING.items():
        if known_model in model_lower or model_lower in known_model:
            return pricing

    # Model family matching
    if 'opus' in model_lower:
        return MODEL_PRICING.get("claude-opus-4-5-20251101", DEFAULT_PRICING)
    elif 'sonnet' in model_lower:
        return MODEL_PRICING.get("claude-sonnet-4-5-20250929", DEFAULT_PRICING)
    elif 'haiku' in model_lower:
        return MODEL_PRICING.get("claude-haiku-3-5-20241022", DEFAULT_PRICING)

    return DEFAULT_PRICING


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    model: str = "unknown"
) -> CostBreakdown:
    """
    Calculate cost for token usage.

    Args:
        input_tokens: Number of input tokens (non-cached)
        output_tokens: Number of output tokens
        cache_read_tokens: Number of tokens read from cache
        cache_write_tokens: Number of tokens written to cache
        model: Model identifier

    Returns:
        CostBreakdown with detailed costs
    """
    pricing = get_model_pricing(model)

    input_cost = (input_tokens / 1_000_000) * pricing["input_per_million"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_million"]
    cache_read_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read_per_million"]
    cache_write_cost = (cache_write_tokens / 1_000_000) * pricing["cache_write_per_million"]

    total_cost = input_cost + output_cost + cache_read_cost + cache_write_cost

    return CostBreakdown(
        input_cost=round(input_cost, 4),
        output_cost=round(output_cost, 4),
        cache_read_cost=round(cache_read_cost, 4),
        cache_write_cost=round(cache_write_cost, 4),
        total_cost=round(total_cost, 4),
        model=model
    )


def calculate_session_cost(session: Dict) -> CostBreakdown:
    """Calculate cost for a session dictionary."""
    return calculate_cost(
        input_tokens=session.get('input_tokens', 0),
        output_tokens=session.get('output_tokens', 0),
        cache_read_tokens=session.get('cache_read_tokens', 0),
        cache_write_tokens=session.get('cache_write_tokens', 0),
        model=session.get('model', 'unknown')
    )


def calculate_daily_cost(usage_data: Dict) -> Dict:
    """
    Calculate costs for a day's usage data.

    Args:
        usage_data: Output from claude_usage_reader.get_todays_usage()

    Returns:
        Dict with cost breakdowns by session and totals
    """
    session_costs = []
    total_breakdown = {
        'input_cost': 0,
        'output_cost': 0,
        'cache_read_cost': 0,
        'cache_write_cost': 0,
        'total_cost': 0
    }

    for session in usage_data.get('sessions', []):
        cost = calculate_session_cost(session)
        session_costs.append({
            'session_id': session.get('session_id'),
            'model': cost.model,
            'cost': cost.total_cost,
            'breakdown': {
                'input': cost.input_cost,
                'output': cost.output_cost,
                'cache_read': cost.cache_read_cost,
                'cache_write': cost.cache_write_cost
            }
        })

        total_breakdown['input_cost'] += cost.input_cost
        total_breakdown['output_cost'] += cost.output_cost
        total_breakdown['cache_read_cost'] += cost.cache_read_cost
        total_breakdown['cache_write_cost'] += cost.cache_write_cost
        total_breakdown['total_cost'] += cost.total_cost

    # Round totals
    for key in total_breakdown:
        total_breakdown[key] = round(total_breakdown[key], 4)

    # Calculate by model
    cost_by_model = {}
    for model_name, model_data in usage_data.get('by_model', {}).items():
        cost = calculate_cost(
            input_tokens=model_data.get('input_tokens', 0),
            output_tokens=model_data.get('output_tokens', 0),
            cache_read_tokens=model_data.get('cache_read_tokens', 0),
            cache_write_tokens=model_data.get('cache_write_tokens', 0),
            model=model_name
        )
        cost_by_model[model_name] = {
            'total_cost': cost.total_cost,
            'breakdown': {
                'input': cost.input_cost,
                'output': cost.output_cost,
                'cache_read': cost.cache_read_cost,
                'cache_write': cost.cache_write_cost
            }
        }

    return {
        'date': usage_data.get('date'),
        'session_costs': session_costs,
        'total': total_breakdown,
        'by_model': cost_by_model
    }


def format_cost(amount: float) -> str:
    """Format a cost amount for display."""
    if amount >= 1:
        return f"${amount:.2f}"
    elif amount >= 0.01:
        return f"${amount:.3f}"
    else:
        return f"${amount:.4f}"


def format_tokens(count: int) -> str:
    """Format token count for display."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


# CLI for testing
if __name__ == "__main__":
    print("=" * 60)
    print("Cost Calculator - Test Run")
    print("=" * 60)

    # Test calculation
    print("\nTest: Opus 4.5 usage")
    cost = calculate_cost(
        input_tokens=10000,
        output_tokens=50000,
        cache_read_tokens=100000,
        cache_write_tokens=15000,
        model="claude-opus-4-5-20251101"
    )
    print(f"  Input cost: {format_cost(cost.input_cost)}")
    print(f"  Output cost: {format_cost(cost.output_cost)}")
    print(f"  Cache read cost: {format_cost(cost.cache_read_cost)}")
    print(f"  Cache write cost: {format_cost(cost.cache_write_cost)}")
    print(f"  Total: {format_cost(cost.total_cost)}")

    print("\nTest: Sonnet 4.5 usage")
    cost = calculate_cost(
        input_tokens=10000,
        output_tokens=50000,
        cache_read_tokens=100000,
        cache_write_tokens=15000,
        model="claude-sonnet-4-5-20250929"
    )
    print(f"  Total: {format_cost(cost.total_cost)}")

    print("\nPricing table:")
    for model, pricing in MODEL_PRICING.items():
        print(f"\n  {model}:")
        print(f"    Input: ${pricing['input_per_million']}/M")
        print(f"    Output: ${pricing['output_per_million']}/M")
        print(f"    Cache read: ${pricing['cache_read_per_million']}/M")
        print(f"    Cache write: ${pricing['cache_write_per_million']}/M")
