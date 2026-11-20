"""Continuous ARBIS scanner. Safe default: public data + paper execution only."""
from __future__ import annotations

import argparse
import logging
import signal
import time
from datetime import datetime, timezone

import ccxt

from config import EXCHANGE_IDS, SYMBOLS
from core.paper_broker import PaperBroker
from core.store import Store
from core.orderbook import evaluate_route

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("arbis")
STOP = False


def _stop(*_):
    global STOP
    STOP = True


def make_exchange(exchange_id: str):
    aliases = {"gate": ("gate", "gateio"), "gateio": ("gateio", "gate"),
               "htx": ("htx", "huobi")}
    cls = None
    for candidate in aliases.get(exchange_id, (exchange_id,)):
        cls = getattr(ccxt, candidate, None)
        if cls is not None:
            break
    if cls is None:
        log.warning("%s is not available in the installed CCXT package", exchange_id)
        return None
    return cls({"enableRateLimit": True, "timeout": 12000, "options": {"defaultType": "spot"}})


def scan_once(exchanges, symbols, store, min_edge_pct, quantity, execute_paper):
    books = {}
    fees = {}
    now = datetime.now(timezone.utc).isoformat()
    for exchange_id, exchange in exchanges.items():
        try:
            markets = exchange.load_markets()
            for symbol in symbols:
                market = markets.get(symbol)
                if not market or not market.get("spot") or market.get("active") is False:
                    continue
                if not exchange.has.get("fetchOrderBook"):
                    continue
                book = exchange.fetch_order_book(symbol, 20)
                if not book.get("timestamp"):
                    continue
                books[(exchange_id, symbol)] = book
                fee = market.get("taker")
                if fee is not None and 0 <= float(fee) < 1:
                    fees[(exchange_id, symbol)] = float(fee)
                store.record_observation(exchange_id, symbol, now, {
                    "timestamp": book.get("timestamp"),
                    "bids": book.get("bids", [])[:20],
                    "asks": book.get("asks", [])[:20],
                })
        except Exception as exc:
            log.warning("%s collection error: %s", exchange_id, str(exc)[:200])

    candidates = 0
    broker = PaperBroker(store) if execute_paper else None
    for symbol in symbols:
        venues = [venue for venue in exchanges if (venue, symbol) in books and (venue, symbol) in fees]
        for buy_venue in venues:
            for sell_venue in venues:
                if buy_venue == sell_venue:
                    continue
                route = evaluate_route(
                    books[(buy_venue, symbol)], books[(sell_venue, symbol)],
                    quantity, fees[(buy_venue, symbol)], fees[(sell_venue, symbol)],
                    min_net_edge_pct=min_edge_pct,
                )
                if not route or not route["profitable"]:
                    continue
                candidates += 1
                log.info(
                    "PAPER CANDIDATE %s buy=%s sell=%s qty=%s net=%s (%s%%)",
                    symbol, buy_venue, sell_venue, quantity,
                    round(route["net_pnl"], 8), round(route["net_edge_pct"], 5),
                )
                if broker:
                    result = broker.execute({
                        "symbol": symbol, "buy_exchange": buy_venue,
                        "sell_exchange": sell_venue, "buy_book": books[(buy_venue, symbol)],
                        "sell_book": books[(sell_venue, symbol)], "quantity": quantity,
                        "buy_fee": fees[(buy_venue, symbol)],
                        "sell_fee": fees[(sell_venue, symbol)],
                    }, min_edge_pct)
                    if result.get("status") == "simulated_fill":
                        log.info("PAPER FILLED id=%s net_pnl=%s", result["id"], result["net_pnl"])
    log.info("scan complete: venues=%d books=%d candidates=%d", len(exchanges), len(books), candidates)
    return candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--quantity", type=float, default=0.001)
    parser.add_argument("--min-edge-pct", type=float, default=0.10)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-paper", action="store_true")
    args = parser.parse_args()

    if args.interval < 1 or args.quantity <= 0:
        parser.error("interval must be >= 1 second and quantity must be positive")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    exchanges = {}
    for exchange_id in EXCHANGE_IDS:
        instance = make_exchange(exchange_id)
        if instance is not None:
            exchanges[exchange_id] = instance
    store = Store()
    log.info("ARBIS starting: %d exchange adapters, %d symbols, mode=PAPER",
             len(exchanges), len(SYMBOLS))
    try:
        while not STOP:
            started = time.monotonic()
            scan_once(exchanges, SYMBOLS, store, args.min_edge_pct, args.quantity, not args.no_paper)
            if args.once:
                break
            time.sleep(max(0, args.interval - (time.monotonic() - started)))
    finally:
        for exchange in exchanges.values():
            try:
                exchange.close()
            except Exception:
                pass
        log.info("paper ledger summary: %s", store.summary())


if __name__ == "__main__":
    main()
