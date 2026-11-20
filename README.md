# ARBIS — Arbitrage Intelligence System

Python-first cryptocurrency market surveillance and arbitrage research platform.

## Current scope

- Streamlit dashboard using Streamlit's default UI.
- Live public spot ticker collection from Binance, Bybit and OKX through CCXT.
- Cross-exchange bid/ask comparison for configured USDT pairs.
- Transparent fee handling: net estimates are shown only when both markets expose a taker-fee value. Public/default fee metadata is an estimate, not the user's account-specific fee tier.
- No fabricated prices, sample opportunities, seeded trades or placeholder performance figures.
- No private API keys and no live order execution.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Configuration

Copy `.env.example` to `.env` if you want to override the default symbols or request timeout. The initial version uses public market endpoints and does not require exchange credentials.

- `ARBIS_SYMBOLS`: comma-separated CCXT spot symbols, default `BTC/USDT,ETH/USDT,SOL/USDT`.
- `ARBIS_REQUEST_TIMEOUT_MS`: exchange request timeout in milliseconds, default `10000`.

## Data integrity rules

1. Only successful exchange responses are displayed as market data.
2. Failed or stale responses are reported as unavailable; they are never replaced with invented values.
3. A cross-exchange opportunity requires a valid buy ask and sell bid from different venues.
4. Net estimates are omitted when taker-fee metadata is missing.
5. Displayed public fee metadata may differ from account-specific fees, discounts and actual execution costs.
6. The scanner does not account for transfer, withdrawal, funding, inventory, latency or market-impact costs. A displayed spread is not a guaranteed executable arbitrage.
7. The application is monitoring/research software. It does not place orders.

## Deployment

Deploy the Streamlit dashboard on a host that supports Streamlit. For reliable 24/7 market collection, run the collector as a separate always-on worker; do not rely on a dashboard process or free-tier app sleeping behavior as a continuous data service.

## Regulatory and operational note

Use public endpoints for the initial release. Verify applicable UAE requirements, exchange eligibility and exchange terms before enabling any trading or third-party service functionality.
