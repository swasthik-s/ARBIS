# ARBIS — Arbitrage Intelligence System

Python-first cryptocurrency market surveillance and arbitrage research platform.

## Current scope

- Streamlit dashboard using Streamlit's default UI.
- Configurable multi-exchange public spot ticker collection through CCXT.
- Default exchange universe: Binance, Bybit, OKX, KuCoin, Gate, Bitget, MEXC, Crypto.com, Coinbase, Kraken, Bitstamp, Gemini, Bitfinex, BingX, Phemex, Poloniex, Bitvavo, BitMart, CoinEx, LBank, DigiFinex, HTX, WhiteBIT, Backpack, HashKey, Bitrue, Bitso, bitbank, bitFlyer and Bithumb.
- Cross-exchange bid/ask comparison for configured symbols.
- Ranked candidate view: only comparisons with known public taker-fee metadata and fee-adjusted net edge above a configurable threshold are shown as candidates. Raw pairwise combinations are not labelled as opportunities.
- Candidate status is preliminary until order-book depth and execution constraints are validated.
- Freshness-aware comparisons: quotes without a valid exchange timestamp or older than the configured threshold are excluded from spread calculations.
- Transparent fee handling: net estimates are shown only when both markets expose a taker-fee value. Public/default fee metadata is not the user's account-specific fee tier.
- No fabricated prices, sample opportunities, seeded trades or placeholder performance figures.
- No private API keys and no live order execution.

CCXT currently documents support for more than 100 exchange APIs. ARBIS deliberately starts with a curated subset of spot-capable centralized venues rather than indiscriminately querying every adapter. Some CCXT exchange IDs differ by library version; an unavailable adapter is reported explicitly.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

## Configuration

Copy `.env.example` to `.env` to override settings.

- `ARBIS_SYMBOLS`: comma-separated CCXT symbols, default `BTC/USDT,ETH/USDT,SOL/USDT`.
- `ARBIS_EXCHANGES`: comma-separated CCXT exchange IDs. Defaults to the curated exchange universe in `config.py`.
- `ARBIS_REQUEST_TIMEOUT_MS`: request timeout in milliseconds, default `10000`.
- `ARBIS_MAX_DATA_AGE_SECONDS`: maximum quote age for spread calculations, default `30`.
- `ARBIS_MAX_EXCHANGE_WORKERS`: concurrent exchange workers, default `6`.
- `ARBIS_MIN_NET_EDGE_PCT`: minimum fee-adjusted estimated net edge to display as a candidate, default `0.10` percent.

## Data integrity rules

1. Only actual exchange API responses are displayed as market data.
2. Configured, supported, reachable, responding and usable are different states. A configured venue is not assumed to be accessible.
3. Failed or stale responses remain unavailable; they are never replaced with invented values.
4. A spread comparison requires timestamped fresh bid/ask quotes from two different venues for the same symbol.
5. Net estimates are omitted when taker-fee metadata is missing.
6. Public fee metadata may differ from account-specific fees, discounts and actual execution costs.
7. The scanner does not yet account for transfer, withdrawal, funding, inventory, latency, market impact or partial-fill costs. A displayed spread is not a guaranteed executable arbitrage.
8. The application does not place orders.

## Market coverage roadmap

- Current: centralized spot market adapters through CCXT.
- Next: separate derivatives adapters for perpetual swaps, dated futures and funding rates. These must use contract-aware symbols and contract metadata, not be mixed into spot comparisons.
- Later: dedicated DEX/on-chain adapters for pool reserves, swap quotes, gas, MEV and chain finality. DEX data must not be treated as a centralized exchange ticker.

## Deployment

Deploy the Streamlit dashboard on a host that supports Streamlit. For reliable 24/7 collection, run a separate always-on collector/worker and persist timestamped observations. Streamlit Community Cloud should not be treated as an always-on market-data worker.

## UAE and operational note

This exchange list is a technical integration list, not a UAE regulatory approval list or a guarantee that a platform will serve a UAE resident. Check the exact contracting entity, licensed activity, product eligibility, exchange terms and hosting-region access before using an exchange or enabling execution. VARA's public register is the primary source for Dubai (excluding DIFC) VASP status: https://www.vara.ae/en/licenses-and-register/public-register/
