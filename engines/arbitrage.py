"""Cross-exchange spot spread calculations using observed bid/ask prices."""
from itertools import permutations
from typing import Any


def find_cross_exchange_opportunities(
    market_data: list[dict[str, Any]],
    symbols: tuple[str, ...] | list[str],
) -> list[dict[str, Any]]:
    """Return observed cross-venue spreads. Never invent missing prices or fees."""
    opportunities: list[dict[str, Any]] = []

    for symbol in symbols:
        rows = [
            row for row in market_data
            if row.get("symbol") == symbol
            and isinstance(row.get("bid"), (int, float)) and row["bid"] > 0
            and isinstance(row.get("ask"), (int, float)) and row["ask"] > 0
            and row["bid"] <= row["ask"]
        ]

        for buy, sell in permutations(rows, 2):
            if buy["exchange"] == sell["exchange"]:
                continue

            buy_ask = float(buy["ask"])
            sell_bid = float(sell["bid"])
            gross_per_unit = sell_bid - buy_ask
            gross_pct = (gross_per_unit / buy_ask) * 100

            buy_fee = buy.get("taker_fee")
            sell_fee = sell.get("taker_fee")
            net_per_unit = None
            net_pct = None

            if (
                isinstance(buy_fee, (int, float)) and 0 <= buy_fee < 1
                and isinstance(sell_fee, (int, float)) and 0 <= sell_fee < 1
            ):
                buy_cost = buy_ask * (1 + float(buy_fee))
                sell_proceeds = sell_bid * (1 - float(sell_fee))
                net_per_unit = sell_proceeds - buy_cost
                net_pct = (net_per_unit / buy_cost) * 100

            opportunities.append({
                "symbol": symbol,
                "buy_exchange": buy["exchange"],
                "sell_exchange": sell["exchange"],
                "buy_ask": buy_ask,
                "sell_bid": sell_bid,
                "gross_spread": gross_per_unit,
                "gross_spread_pct": gross_pct,
                "net_per_unit": net_per_unit,
                "net_pct": net_pct,
                "buy_quote_volume": buy.get("quote_volume"),
                "sell_quote_volume": sell.get("quote_volume"),
                "buy_timestamp": buy.get("timestamp"),
                "sell_timestamp": sell.get("timestamp"),
                "fee_basis": "public market metadata; verify account tier" if net_pct is not None else "fee metadata unavailable",
            })

    return sorted(opportunities, key=lambda item: item["gross_spread_pct"], reverse=True)
