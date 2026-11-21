import pytest

from core.risk import RiskLimits, RiskRejected, validate_order_intent


def valid_intent(**overrides):
    values = dict(
        mode="TESTNET", symbol="BTC/USDT", quantity=0.001,
        reference_price=50000, estimated_net_edge_pct=0.3,
        book_age_ms=500, daily_realized_pnl=0, open_orders=0,
        current_position_quote=0, limits=RiskLimits(),
    )
    values.update(overrides)
    return values


def test_valid_testnet_intent_passes():
    validate_order_intent(**valid_intent())


@pytest.mark.parametrize("override", [
    {"mode": "LIVE"}, {"quantity": 0}, {"book_age_ms": 5000},
    {"estimated_net_edge_pct": 0.01}, {"daily_realized_pnl": -25},
    {"open_orders": 2}, {"current_position_quote": 250},
])
def test_risky_intents_are_rejected(override):
    with pytest.raises(RiskRejected):
        validate_order_intent(**valid_intent(**override))
