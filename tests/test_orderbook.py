from core.orderbook import evaluate_route, simulate_book_fill


def test_depth_fill_calculates_vwap():
    book = {"asks": [[100, 1], [102, 2]], "timestamp": 100000}
    fill = simulate_book_fill(book, "buy", 2)
    assert fill["notional"] == 202
    assert fill["vwap"] == 101


def test_insufficient_depth_rejects_route():
    buy = {"asks": [[100, 0.5]], "timestamp": 100000}
    sell = {"bids": [[105, 0.5]], "timestamp": 100000}
    assert evaluate_route(buy, sell, 1, 0.001, 0.001, now_ms=100000) is None


def test_fees_can_turn_gross_spread_negative():
    buy = {"asks": [[100, 2]], "timestamp": 100000}
    sell = {"bids": [[100.1, 2]], "timestamp": 100000}
    result = evaluate_route(buy, sell, 1, 0.001, 0.001, now_ms=100000)
    assert result is not None
    assert result["net_pnl"] < 0
    assert result["profitable"] is False


def test_positive_depth_route():
    buy = {"asks": [[100, 2]], "timestamp": 100000}
    sell = {"bids": [[102, 2]], "timestamp": 100000}
    result = evaluate_route(buy, sell, 1, 0.001, 0.001, 0.1, now_ms=100000)
    assert result["profitable"]
    assert result["net_pnl"] > 0
