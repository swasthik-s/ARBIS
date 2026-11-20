from core.store import Store


def test_trade_ledger_and_route_deduplication(tmp_path):
    store = Store(str(tmp_path / "arbis.sqlite3"))
    trade = {
        "id": "trade-1",
        "created_at": "2026-11-21T00:00:00+00:00",
        "symbol": "BTC/USDT",
        "buy_exchange": "venue_a",
        "sell_exchange": "venue_b",
        "net_pnl": 1.25,
        "net_edge_pct": 0.2,
        "route_key": "BTC/USDT|venue_a|venue_b|1000|1001",
    }
    assert store.record_trade(trade) is True
    duplicate = dict(trade, id="trade-2")
    assert store.record_trade(duplicate) is False
    summary = store.summary()
    assert summary["trades"] == 1
    assert summary["net_pnl"] == 1.25
    assert summary["win_rate_pct"] == 100.0
