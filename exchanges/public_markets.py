"""Public spot market collection across configured CCXT exchanges."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import ccxt

from config import EXCHANGE_IDS, REQUEST_TIMEOUT_MS, MAX_EXCHANGE_WORKERS

BINANCE_MARKET_DATA_BASE = "https://data-api.binance.vision"

EXCHANGE_ALIASES = {
    "gate": ("gate", "gateio"),
    "gateio": ("gateio", "gate"),
    "htx": ("htx", "huobi"),
}


def _binance_public_markets(symbols: tuple[str, ...]) -> dict[str, Any]:
    """Fetch unauthenticated Binance public spot data from its market-data host."""
    result = {
        "exchange": "binance",
        "status": "error",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "rows": [],
        "error": None,
        "connection_method": "official_market_data_only_rest",
        "api_host": BINANCE_MARKET_DATA_BASE,
    }

    def get_json(path: str, params: dict[str, str] | None = None):
        query = "?" + urlencode(params) if params else ""
        request = Request(
            BINANCE_MARKET_DATA_BASE + path + query,
            headers={"Accept": "application/json", "User-Agent": "ARBIS/1.0"},
        )
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_MS / 1000) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 451:
                raise RuntimeError("regional_restriction_http_451") from exc
            if exc.code == 403:
                raise RuntimeError("access_denied_http_403") from exc
            if exc.code == 429:
                raise RuntimeError("rate_limited_http_429") from exc
            raise

    try:
        exchange_info = get_json("/api/v3/exchangeInfo")
        markets = {item.get("symbol"): item for item in exchange_info.get("symbols", [])}
        for symbol in symbols:
            market_id = symbol.replace("/", "").replace(":", "")
            market = markets.get(market_id)
            if not market or market.get("status") != "TRADING":
                continue
            if not market.get("isSpotTradingAllowed", True):
                continue
            ticker = get_json("/api/v3/ticker/24hr", {"symbol": market_id})
            close_time = ticker.get("closeTime")
            timestamp = (
                datetime.fromtimestamp(close_time / 1000, tz=timezone.utc).isoformat()
                if close_time else None
            )
            result["rows"].append({
                "exchange": "binance",
                "symbol": symbol,
                "bid": float(ticker["bidPrice"]) if ticker.get("bidPrice") else None,
                "ask": float(ticker["askPrice"]) if ticker.get("askPrice") else None,
                "last": float(ticker["lastPrice"]) if ticker.get("lastPrice") else None,
                "quote_volume": float(ticker["quoteVolume"]) if ticker.get("quoteVolume") else None,
                "timestamp": timestamp,
                "taker_fee": None,
                "fee_status": "account_or_symbol_specific_fee_not_loaded",
            })
        result["status"] = "connected" if result["rows"] else "connected_no_selected_spot_pairs"
    except Exception as exc:
        message = str(exc)
        result["error"] = f"{type(exc).__name__}: {message}"[:400]
        if "regional_restriction_http_451" in message:
            result["status"] = "regional_restriction"
        elif "rate_limited_http_429" in message:
            result["status"] = "rate_limited"
        elif "access_denied_http_403" in message:
            result["status"] = "access_denied"
    return result


def _exchange_class(exchange_id: str):
    for candidate in EXCHANGE_ALIASES.get(exchange_id, (exchange_id,)):
        exchange_class = getattr(ccxt, candidate, None)
        if exchange_class is not None:
            return exchange_class
    return None


def _fetch_tickers(exchange, symbols: list[str]) -> dict[str, Any]:
    if exchange.has.get("fetchTickers"):
        try:
            return exchange.fetch_tickers(symbols)
        except Exception:
            pass
    tickers: dict[str, Any] = {}
    for symbol in symbols:
        try:
            tickers[symbol] = exchange.fetch_ticker(symbol)
        except Exception:
            continue
    return tickers


def _fetch_exchange(exchange_id: str, symbols: tuple[str, ...]) -> dict[str, Any]:
    if exchange_id == "binance":
        return _binance_public_markets(symbols)

    exchange_class = _exchange_class(exchange_id)
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
            if symbol in markets and markets[symbol].get("spot")
            and markets[symbol].get("active") is not False
        ]
        if not available:
            result["status"] = "connected_no_selected_spot_pairs"
            return result

        tickers = _fetch_tickers(exchange, available)
        for symbol in available:
            ticker = tickers.get(symbol) or {}
            timestamp_ms = ticker.get("timestamp")
            ticker_datetime = ticker.get("datetime")
            timestamp = None
            if timestamp_ms:
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()
            elif ticker_datetime:
                timestamp = ticker_datetime
            result["rows"].append({
                "exchange": exchange_id,
                "symbol": symbol,
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
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
    """Fetch configured venues concurrently; preserve explicit per-venue failures."""
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
