"""Public spot market data adapters powered by CCXT."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import ccxt

from config import EXCHANGE_IDS, REQUEST_TIMEOUT_MS


def _fetch_exchange(exchange_id: str, symbols: tuple[str, ...]) -> dict[str, Any]:
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        "enableRateLimit": True,
        "timeout": REQUEST_TIMEOUT_MS,
        "options": {"defaultType": "spot"},
    })
    result: dict[str, Any] = {
        "exchange": exchange_id,
        "status": "error",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "rows": [],
        "error": None,
    }

    try:
        markets = exchange.load_markets()
        available = [
            symbol for symbol in symbols
            if symbol in markets
            and markets[symbol].get("spot")
            and markets[symbol].get("active") is not False
        ]

        if not available:
            result["status"] = "connected_no_symbols"
            return result

        tickers = exchange.fetch_tickers(available)
        for symbol in available:
            ticker = tickers.get(symbol) or {}
            bid, ask = ticker.get("bid"), ticker.get("ask")
            market = markets[symbol]
            timestamp_ms = ticker.get("timestamp")
            result["rows"].append({
                "exchange": exchange_id,
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "last": ticker.get("last"),
                "quote_volume": ticker.get("quoteVolume"),
                "timestamp": (
                    datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()
                    if timestamp_ms else None
                ),
                "taker_fee": market.get("taker"),
            })

        result["status"] = "connected"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:300]
    finally:
        try:
            exchange.close()
        except Exception:
            pass

    return result


def fetch_public_markets(symbols: tuple[str, ...]) -> list[dict[str, Any]]:
    """Fetch configured symbols concurrently; failed venues remain explicit errors."""
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(EXCHANGE_IDS)) as pool:
        futures = {
            pool.submit(_fetch_exchange, exchange_id, symbols): exchange_id
            for exchange_id in EXCHANGE_IDS
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                exchange_id = futures[future]
                results.append({
                    "exchange": exchange_id,
                    "status": "error",
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "rows": [],
                    "error": f"{type(exc).__name__}: {exc}"[:300],
                })
    return sorted(results, key=lambda item: item["exchange"])
