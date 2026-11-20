from engines.arbitrage import find_cross_exchange_opportunities


def test_uses_observed_bid_ask_and_computes_fee_adjusted_net():
    rows = [
        {
            "exchange": "venue_a", "symbol": "BTC/USDT",
            "ask": 100.0, "bid": 99.0, "taker_fee": 0.001,
        },
        {
            "exchange": "venue_b", "symbol": "BTC/USDT",
            "ask": 103.0, "bid": 102.0, "taker_fee": 0.001,
        },
    ]
    results = find_cross_exchange_opportunities(rows, ["BTC/USDT"])
    forward = next(
        item for item in results
        if item["buy_exchange"] == "venue_a" and item["sell_exchange"] == "venue_b"
    )
    assert forward["gross_spread"] == 2.0
    assert forward["net_per_unit"] is not None
    assert forward["net_per_unit"] < forward["gross_spread"]


def test_missing_fee_metadata_does_not_invent_net_profit():
    rows = [
        {"exchange": "venue_a", "symbol": "ETH/USDT", "ask": 10.0, "bid": 9.0, "taker_fee": None},
        {"exchange": "venue_b", "symbol": "ETH/USDT", "ask": 11.0, "bid": 10.5, "taker_fee": 0.001},
    ]
    results = find_cross_exchange_opportunities(rows, ["ETH/USDT"])
    forward = next(
        item for item in results
        if item["buy_exchange"] == "venue_a" and item["sell_exchange"] == "venue_b"
    )
    assert forward["net_per_unit"] is None
    assert forward["net_pct"] is None


def test_rejects_invalid_bid_ask_rows():
    rows = [
        {"exchange": "venue_a", "symbol": "BTC/USDT", "ask": 0, "bid": 99},
        {"exchange": "venue_b", "symbol": "BTC/USDT", "ask": 100, "bid": 101},
    ]
    assert find_cross_exchange_opportunities(rows, ["BTC/USDT"]) == []
