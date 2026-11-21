"""Fail-closed execution risk policy. Live trading is intentionally disabled."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_order_quote: float = 100.0
    max_daily_loss_quote: float = 25.0
    max_open_orders: int = 2
    max_position_quote: float = 250.0
    max_book_age_ms: int = 1500
    min_net_edge_pct: float = 0.15


class RiskRejected(ValueError):
    pass


def validate_order_intent(*, mode, symbol, quantity, reference_price,
                           estimated_net_edge_pct, book_age_ms,
                           daily_realized_pnl, open_orders,
                           current_position_quote, limits):
    if mode not in {"PAPER", "TESTNET"}:
        raise RiskRejected("Only PAPER and TESTNET modes are enabled.")
    if not symbol or "/" not in symbol:
        raise RiskRejected("A valid unified spot symbol is required.")
    if quantity <= 0 or reference_price <= 0:
        raise RiskRejected("Quantity and reference price must be positive.")
    notional = quantity * reference_price
    if notional > limits.max_order_quote:
        raise RiskRejected("Order notional exceeds the configured per-order limit.")
    if estimated_net_edge_pct < limits.min_net_edge_pct:
        raise RiskRejected("Estimated net edge is below the minimum threshold.")
    if book_age_ms < 0 or book_age_ms > limits.max_book_age_ms:
        raise RiskRejected("Market data is stale or has an invalid timestamp.")
    if daily_realized_pnl <= -abs(limits.max_daily_loss_quote):
        raise RiskRejected("Daily loss limit has been reached.")
    if open_orders >= limits.max_open_orders:
        raise RiskRejected("Maximum open-order count reached.")
    if current_position_quote + notional > limits.max_position_quote:
        raise RiskRejected("Position exposure limit would be exceeded.")
