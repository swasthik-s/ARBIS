"""ARBIS dashboard: observed public market data only."""
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from arbis_config import (
    EXCHANGE_IDS, EXCHANGE_NAMES, MAX_DATA_AGE_SECONDS, SYMBOLS,
)
from engines.arbitrage import find_cross_exchange_opportunities
from exchanges.public_markets import fetch_public_markets

st.set_page_config(page_title="ARBIS", page_icon="📊", layout="wide")
st.title("ARBIS")
st.caption("Arbitrage Intelligence System · Multi-exchange public market surveillance")

with st.sidebar:
    st.header("Market settings")
    selected_exchanges = st.multiselect(
        "Exchanges",
        options=list(EXCHANGE_IDS),
        default=list(EXCHANGE_IDS),
        format_func=lambda value: EXCHANGE_NAMES.get(value, value.upper()),
    )
    st.write("**Market type:** Spot")
    selected_symbols = st.multiselect(
        "Trading pairs",
        options=list(SYMBOLS),
        default=list(SYMBOLS),
    )
    refresh = st.button("Refresh market data", type="primary", use_container_width=True)
    st.caption(
        "Public endpoints only. No exchange credentials, account access or order execution. "
        "Configured exchanges are not necessarily reachable from this hosting region."
    )

if "market_results" not in st.session_state:
    st.session_state.market_results = []
    st.session_state.last_fetch = None
    st.session_state.last_selection = None

selection = (tuple(selected_exchanges), tuple(selected_symbols))
selection_changed = st.session_state.last_selection != selection

if refresh or st.session_state.last_fetch is None or selection_changed:
    with st.spinner(f"Requesting live market data from {len(selected_exchanges)} exchanges..."):
        st.session_state.market_results = fetch_public_markets(
            tuple(selected_symbols), tuple(selected_exchanges)
        )
        st.session_state.last_fetch = datetime.now(timezone.utc)
        st.session_state.last_selection = selection

results = st.session_state.market_results
connected_statuses = {"connected", "connected_no_selected_spot_pairs", "connected_no_ticker_data"}
connected = [r for r in results if r["status"] in connected_statuses]
failed = [r for r in results if r["status"] not in connected_statuses]
all_rows = [row for result in results for row in result["rows"]]

now = datetime.now(timezone.utc)
fresh_rows = []
quote_rows = []
for row in all_rows:
    age_seconds = None
    if row.get("timestamp"):
        try:
            timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            age_seconds = (now - timestamp).total_seconds()
        except (ValueError, TypeError):
            pass
    is_fresh = age_seconds is not None and -5 <= age_seconds <= MAX_DATA_AGE_SECONDS
    if is_fresh and row.get("bid") and row.get("ask"):
        fresh_rows.append(row)
    quote_rows.append({
        "Exchange": EXCHANGE_NAMES.get(row["exchange"], row["exchange"].upper()),
        "Pair": row["symbol"],
        "Bid": row.get("bid"),
        "Ask": row.get("ask"),
        "Last": row.get("last"),
        "24h Quote Volume": row.get("quote_volume"),
        "Quote age (seconds)": round(age_seconds, 1) if age_seconds is not None else None,
        "Fresh": is_fresh,
        "Taker fee metadata": row.get("taker_fee"),
    })

if not selected_exchanges:
    st.info("Select at least one exchange in the sidebar.")
elif not selected_symbols:
    st.info("Select at least one trading pair in the sidebar.")
else:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Exchanges responding", f"{len(connected)} / {len(selected_exchanges)}")
    col2.metric("Ticker records", len(all_rows))
    col3.metric("Fresh bid/ask quotes", len(fresh_rows))
    opportunities = find_cross_exchange_opportunities(fresh_rows, selected_symbols)
    col4.metric("Fresh cross-venue comparisons", len(opportunities))

    st.subheader("Exchange connectivity")
    status_rows = [{
        "Exchange": EXCHANGE_NAMES.get(r["exchange"], r["exchange"].upper()),
        "CCXT ID": r["exchange"],
        "Status": r["status"],
        "Pairs returned": len(r["rows"]),
        "Last request (UTC)": r["received_at"],
        "Error": r.get("error") or "",
    } for r in results]
    st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)

    if failed:
        st.warning("Some configured exchanges did not return usable responses. No values are substituted.")
        for result in failed:
            st.caption(
                f'{EXCHANGE_NAMES.get(result["exchange"], result["exchange"].upper())}: '
                f'{result.get("error") or result["status"]}'
            )

    st.subheader("Observed market quotes")
    if quote_rows:
        st.dataframe(pd.DataFrame(quote_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No ticker records were returned by the selected exchanges.")

    st.subheader("Cross-exchange spread observations")
    if not opportunities:
        st.info(
            "No fresh cross-exchange bid/ask comparisons are available. "
            "At least two exchanges must return timestamped, fresh quotes for the same pair."
        )
    else:
        opportunity_rows = [{
            "Pair": item["symbol"],
            "Buy venue": EXCHANGE_NAMES.get(item["buy_exchange"], item["buy_exchange"].upper()),
            "Buy ask": item["buy_ask"],
            "Sell venue": EXCHANGE_NAMES.get(item["sell_exchange"], item["sell_exchange"].upper()),
            "Sell bid": item["sell_bid"],
            "Gross spread %": item["gross_spread_pct"],
            "Estimated net %": item["net_pct"],
            "Buy quote timestamp": item["buy_timestamp"],
            "Sell quote timestamp": item["sell_timestamp"],
            "Fee basis": item["fee_basis"],
        } for item in opportunities]
        st.dataframe(pd.DataFrame(opportunity_rows), use_container_width=True, hide_index=True)
        st.caption(
            "These are observed bid/ask comparisons, not confirmed executable arbitrage. "
            "Net estimates use public market fee metadata where available and exclude "
            "account-specific fees, transfer costs, funding, inventory, latency, market impact "
            "and partial-fill risk."
        )

st.divider()
st.caption(
    f"Last collection attempt: "
    f"{st.session_state.last_fetch.isoformat() if st.session_state.last_fetch else 'Not yet collected'} · "
    f"Quote freshness threshold: {MAX_DATA_AGE_SECONDS}s · All timestamps UTC."
)
st.caption("No fabricated or seeded market values. ARBIS does not place orders.")
