import pytest

from core.execution import BinanceSpotTestnet, ExecutionConfigurationError


def test_testnet_adapter_requires_dedicated_credentials(monkeypatch):
    monkeypatch.delenv("ARBIS_BINANCE_TESTNET_API_KEY", raising=False)
    monkeypatch.delenv("ARBIS_BINANCE_TESTNET_SECRET", raising=False)
    with pytest.raises(ExecutionConfigurationError):
        BinanceSpotTestnet()
