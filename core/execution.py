"""Authenticated exchange adapter restricted to Binance Spot Testnet."""
from __future__ import annotations

import os
from typing import Any

import ccxt


class ExecutionConfigurationError(RuntimeError):
    pass


class BinanceSpotTestnet:
    """Testnet-only adapter. This class cannot connect to Binance production."""

    def __init__(self):
        key = os.getenv("ARBIS_BINANCE_TESTNET_API_KEY", "").strip()
        secret = os.getenv("ARBIS_BINANCE_TESTNET_SECRET", "").strip()
        if not key or not secret:
            raise ExecutionConfigurationError(
                "Set ARBIS_BINANCE_TESTNET_API_KEY and ARBIS_BINANCE_TESTNET_SECRET."
            )
        self.exchange = ccxt.binance({
            "apiKey": key,
            "secret": secret,
            "enableRateLimit": True,
            "timeout": 15000,
            "options": {"defaultType": "spot"},
        })
        self.exchange.set_sandbox_mode(True)

    def load_markets(self):
        return self.exchange.load_markets()

    def fetch_balance(self):
        return self.exchange.fetch_balance()

    def create_limit_order(self, symbol: str, side: str, amount: float,
                           price: float, client_order_id: str) -> dict[str, Any]:
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if amount <= 0 or price <= 0:
            raise ValueError("amount and price must be positive")
        return self.exchange.create_order(
            symbol, "limit", side, amount, price,
            {"clientOrderId": client_order_id},
        )

    def fetch_order(self, order_id: str, symbol: str):
        return self.exchange.fetch_order(order_id, symbol)

    def cancel_order(self, order_id: str, symbol: str):
        return self.exchange.cancel_order(order_id, symbol)

    def close(self):
        self.exchange.close()
