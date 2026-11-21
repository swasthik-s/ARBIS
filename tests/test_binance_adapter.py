from exchanges.public_markets import _binance_public_markets


def test_binance_market_data_host_is_official_public_endpoint():
    from exchanges.public_markets import BINANCE_MARKET_DATA_BASE
    assert BINANCE_MARKET_DATA_BASE == "https://data-api.binance.vision"


def test_binance_region_restriction_is_not_relabelled_as_connection(monkeypatch):
    from urllib.error import HTTPError
    import exchanges.public_markets as adapter

    def blocked(*args, **kwargs):
        raise HTTPError("https://data-api.binance.vision/api/v3/exchangeInfo", 451, "Unavailable", {}, None)

    monkeypatch.setattr(adapter, "urlopen", blocked)
    result = _binance_public_markets(("BTC/USDT",))
    assert result["status"] == "regional_restriction"
    assert result["rows"] == []
    assert "regional_restriction_http_451" in result["error"]
