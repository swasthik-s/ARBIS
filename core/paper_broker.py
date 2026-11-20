"""Paper broker: simulates fills from observed order-book snapshots only."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.orderbook import evaluate_route


class PaperBroker:
    def __init__(self, store):
        self.store = store

    def execute(self, opportunity: dict[str, Any], min_net_edge_pct: float) -> dict[str, Any]:
        route = evaluate_route(
            opportunity["buy_book"], opportunity["sell_book"],
            opportunity["quantity"], opportunity["buy_fee"], opportunity["sell_fee"],
            min_net_edge_pct=min_net_edge_pct,
            max_book_age_ms=opportunity.get("max_book_age_ms", 5000),
        )
        if not route or not route["profitable"]:
            return {"status": "rejected", "reason": "route_not_profitable_or_books_stale"}
        trade = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "symbol": opportunity["symbol"],
            "buy_exchange": opportunity["buy_exchange"],
            "sell_exchange": opportunity["sell_exchange"],
            **route,
            "mode": "PAPER",
            "status": "simulated_fill",
            "route_key": "|".join([
                opportunity["symbol"], opportunity["buy_exchange"], opportunity["sell_exchange"],
                str(opportunity["buy_book"].get("timestamp")), str(opportunity["sell_book"].get("timestamp")),
            ]),
        }
        inserted = self.store.record_trade(trade)
        if not inserted:
            return {"status": "duplicate_snapshot", "reason": "this exact book snapshot was already simulated"}
        return trade
