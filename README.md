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

## Deployment — Streamlit is the primary application

The primary ARBIS application is Streamlit. Run the dashboard and scanner together on your Docker host; the dashboard is the control/visibility surface and the worker performs continuous market collection and paper evaluation. Both services share the persistent SQLite data volume.

```bash
cp .env.example .env
docker compose up -d --build
```

Open `http://YOUR_SERVER:8501`. Configure `ARBIS_UI_PORT`, `ARBIS_SCAN_INTERVAL`, `ARBIS_ORDER_QUANTITY`, `ARBIS_MIN_NET_EDGE_PCT`, `ARBIS_SYMBOLS` and `ARBIS_EXCHANGES` in `.env`, then restart with `docker compose up -d --build`. Use `docker compose logs -f arbis-worker` to inspect the scanner and `docker compose logs -f arbis-ui` for the dashboard. Streamlit Community Cloud is not the production runtime for this deployment.

## UAE and operational note

This exchange list is a technical integration list, not a UAE regulatory approval list or a guarantee that a platform will serve a UAE resident. Check the exact contracting entity, licensed activity, product eligibility, exchange terms and hosting-region access before using an exchange or enabling execution. VARA's public register is the primary source for Dubai (excluding DIFC) VASP status: https://www.vara.ae/en/licenses-and-register/public-register/

## Run the continuous paper bot

The scanner is separate from the Streamlit dashboard. It reads public order books, evaluates fixed-size fills across both books, subtracts public taker-fee metadata, rejects stale/insufficient-depth books, and records paper fills in SQLite.

```bash
python bot.py --interval 5 --quantity 0.001 --min-edge-pct 0.10
```

Useful modes:

- `python bot.py --once`: perform one scan and exit.
- `python bot.py --no-paper`: scan and log candidates without recording paper fills.
- `python -m pytest -q`: run deterministic unit tests.

Default operation is PAPER ONLY. It never creates exchange orders and assumes quote/base inventory is already available on both venues. The current paper broker is a research simulator, not an exchange execution emulator: it does not yet model queue position, partial fills over time, inventory limits, withdrawal/transfer settlement, funding, or adverse selection. Do not use its results as proof of live profitability.

The Docker Compose deployment runs both the Streamlit primary app and a separate persistent paper worker against the same durable volume. Paper-only mode remains enforced.

### Binance cloud connectivity

ARBIS uses Binance's official public market-data-only REST host,
`https://data-api.binance.vision`, for the dashboard's Binance spot market
metadata and 24-hour ticker observations. This host is documented by Binance
for unauthenticated public market data; it does not provide account or order
endpoints. The paper scanner is configured to use the same public host for
CCXT public REST calls.

No Binance API key is required for this public-data path. A cloud provider's
egress IP and hosting region still determine whether Binance will serve it.
HTTP 451 is reported as `regional_restriction`; ARBIS does not rotate domains,
use proxies, or otherwise attempt to evade regional restrictions. If the
official market-data host is unavailable from the chosen provider, select a
hosting region/provider where the public API is permitted, subject to the
provider's terms and applicable law.

The Binance dashboard adapter currently does not claim account-specific
taker fees. It marks fee data unavailable until a separate approved fee source
is integrated; therefore it must not be treated as a fee-confirmed arbitrage
candidate solely on ticker data.
