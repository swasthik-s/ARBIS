"""Public spot market collection across configured CCXT exchanges."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import ccxt

from config import EXCHANGE_IDS, REQUEST_TIMEOUT_MS, MAX_EXCHANGE_WORKERS

# CCXT renamed some exchange identifiers across releases. Try compatible aliases.
EXCHANGE_ALIASES = {
    "gate": ("gate", "gateio"),
    "gateio": ("gateio", "gate"),
    "htx": ("htx", "huobi"),
}


def _exchange_class(exchange_id: str):
    candidates = EXCHANGE_ALIASES.get(exchange_id, (exchange_id,))
    for candidate in candidates:
        exchange_class = getattr(ccxt, candidate, None)
        if exchange_class is not None:
            return exchange_class
    return None


def _fetch_tickers(exchange, symbols: list[str]) -> dict[str, Any]:
    """Use bulk ticker endpoint when supported, otherwise fetch symbols individually."""
    if exchange.has.get("fetchTickers"):
        try:
            return exchange.fetch_tickers(symbols)
        except Exception:
            # Some venues allow only one symbol per ticker request.
            # Fall back to individual ticker calls rather than failing the venue.
            pass

    tickers: dict[str, Any] = {}
    for symbol in symbols:
        try:
            tickers[symbol] = exchange.fetch_ticker(symbol)
        except Exception:
            # Keep other symbols from this venue; errors are represented by missing rows.
            continue
    return tickers


def _fetch_exchange(exchange_id: str, symbols: tuple[str, ...]) -> dict[str, Any]:
    if exchange_id == "binance":\n        return _binance_public_markets(symbols)\n\n    exchange_class = _exchange_class(exchange_id)
    result: dict[str, Any] = {
        "exchange": exchange_id,
        "status": "error",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "rows": [],
        "error": None,
    }

    if exchange_class is None:
        result["status"] = "unsupported_in_installed_ccxt"
        result["error"] = "Exchange id is not available in the installed CCXT version."
        return result

    exchange = exchange_class({
        "enableRateLimit": True,
        "timeout": REQUEST_TIMEOUT_MS,
        "options": {"defaultType": "spot"},
    })

    try:
        markets = exchange.load_markets()
        available = [
            symbol for symbol in symbols
            if symbol in markets
            and markets[symbol].get("spot")
            and markets[symbol].get("active") is not False
        ]

        if not available:
            result["status"] = "connected_no_selected_spot_pairs"
            return result

        tickers = _fetch_tickers(exchange, available)
        for symbol in available:
            ticker = tickers.get(symbol) or {}
            bid, ask = ticker.get("bid"), ticker.get("ask")
            timestamp_ms = ticker.get("timestamp")
            ticker_datetime = ticker.get("datetime")
            timestamp = None
            if timestamp_ms:
                timestamp = datetime.fromtimestamp(
                    timestamp_ms / 1000, tz=timezone.utc
                ).isoformat()
            elif ticker_datetime:
                timestamp = ticker_datetime

            result["rows"].append({
                "exchange": exchange_id,
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "last": ticker.get("last"),
                "quote_volume": ticker.get("quoteVolume"),
                "timestamp": timestamp,
                "taker_fee": markets[symbol].get("taker"),
            })

        result["status"] = "connected" if result["rows"] else "connected_no_ticker_data"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:400]
    finally:
        try:
            exchange.close()
        except Exception:
            pass

    return result


def fetch_public_markets(
    symbols: tuple[str, ...],
    exchange_ids: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Fetch configured venues concurrently; every failure remains explicit."""
    selected = exchange_ids if exchange_ids is not None else EXCHANGE_IDS
    if not selected:
        return []

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(MAX_EXCHANGE_WORKERS, len(selected))) as pool:
        futures = {
            pool.submit(_fetch_exchange, exchange_id, symbols): exchange_id
            for exchange_id in selected
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
                    "error": f"{type(exc).__name__}: {exc}"[:400],
                })
    return sorted(results, key=lambda item: item["exchange"])
