"""Depth-aware cross-exchange arbitrage calculations."""
from __future__ import annotations

from typing import Any


def _consume(levels: list, quantity: float, side: str) -> tuple[float, float, float]:
    """Return filled base quantity, quote notional, and worst consumed price."""
    remaining = quantity
    filled = 0.0
    notional = 0.0
    worst_price = 0.0
    for level in levels:
        if len(level) < 2:
            continue
        price, available = float(level[0]), float(level[1])
        if price <= 0 or available <= 0:
            continue
        take = min(remaining, available)
        filled += take
        notional += take * price
        remaining -= take
        worst_price = price
        if remaining <= 1e-12:
            break
    return filled, notional, worst_price


def simulate_book_fill(book: dict[str, Any], side: str, quantity: float) -> dict[str, float] | None:
    levels = book.get("asks" if side == "buy" else "bids") or []
    filled, notional, worst = _consume(levels, quantity, side)
    if filled + 1e-12 < quantity:
        return None
    return {
        "quantity": filled,
        "notional": notional,
        "vwap": notional / filled,
        "worst_price": worst,
    }


def evaluate_route(
    buy_book: dict[str, Any],
    sell_book: dict[str, Any],
    quantity: float,
    buy_fee: float,
    sell_fee: float,
    min_net_edge_pct: float = 0.0,
    max_book_age_ms: int = 5000,
    now_ms: int | None = None,
) -> dict[str, Any] | None:
    """Evaluate a pre-funded cross-venue route at a fixed base quantity.

    Assumes quote/base inventory already exists on both venues. It does not
    assume instant transfers or guarantee fills at the displayed snapshot.
    """
    import time

    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    for book in (buy_book, sell_book):
        ts = book.get("timestamp")
        if ts is None or abs(now_ms - int(ts)) > max_book_age_ms:
            return None

    buy = simulate_book_fill(buy_book, "buy", quantity)
    sell = simulate_book_fill(sell_book, "sell", quantity)
    if not buy or not sell:
        return None

    buy_cost = buy["notional"] * (1 + buy_fee)
    sell_proceeds = sell["notional"] * (1 - sell_fee)
    net = sell_proceeds - buy_cost
    net_pct = (net / buy_cost) * 100 if buy_cost else -100.0
    gross = sell["notional"] - buy["notional"]
    result = {
        "quantity": quantity,
        "buy_vwap": buy["vwap"],
        "sell_vwap": sell["vwap"],
        "buy_worst_price": buy["worst_price"],
        "sell_worst_price": sell["worst_price"],
        "buy_notional": buy["notional"],
        "sell_notional": sell["notional"],
        "gross_pnl": gross,
        "buy_fee": buy["notional"] * buy_fee,
        "sell_fee": sell["notional"] * sell_fee,
        "net_pnl": net,
        "net_edge_pct": net_pct,
        "profitable": net_pct >= min_net_edge_pct,
    }
    return result
