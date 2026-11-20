"""ARBIS Streamlit dashboard. All market figures come from live public exchange responses."""
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from config import MAX_DATA_AGE_SECONDS, SYMBOLS
from engines.arbitrage import find_cross_exchange_opportunities
from exchanges.public_markets import fetch_public_markets

st.set_page_config(page_title="ARBIS", page_icon="📊", layout="wide")
st.title("ARBIS")
st.caption("Arbitrage Intelligence System · Live public market surveillance")

with st.sidebar:
    st.header("Market settings")
    st.write("**Exchanges:** Binance · Bybit · OKX")
    st.write("**Market type:** Spot")
    selected_symbols = st.multiselect(
        "Trading pairs",
        options=list(SYMBOLS),
        default=list(SYMBOLS),
    )
    refresh = st.button("Refresh market data", type="primary", use_container_width=True)
    st.caption("Refresh manually to request fresh exchange data. Public endpoints only; no trading credentials or order execution.")

if "market_results" not in st.session_state:
    st.session_state.market_results = []
    st.session_state.last_fetch = None

if refresh or st.session_state.last_fetch is None:
    with st.spinner("Requesting live public market data from exchanges..."):
        st.session_state.market_results = fetch_public_markets(tuple(selected_symbols))
        st.session_state.last_fetch = datetime.now(timezone.utc)

results = st.session_state.market_results
connected = [r for r in results if r["status"] == "connected"]
failed = [r for r in results if r["status"] == "error"]
all_rows = [row for result in results for row in result["rows"]]

if not selected_symbols:
    st.info("Select at least one trading pair in the sidebar.")
elif not all_rows:
    st.warning("No live ticker data was returned. Check exchange availability and try refreshing.")
else:
    opportunities = find_cross_exchange_opportunities(all_rows, selected_symbols)
    valid_opportunities = [
        item for item in opportunities
        if item["buy_timestamp"] and item["sell_timestamp"]
    ]

    col1, col2, col3 = st.columns(3)
    col1.metric("Exchanges responding", f"{len(connected)} / 3")
    col2.metric("Live ticker records", len(all_rows))
    col3.metric("Observed cross-venue comparisons", len(valid_opportunities))

    st.subheader("Exchange connectivity")
    status_rows = [
        {
            "Exchange": r["exchange"].upper(),
            "Status": r["status"],
            "Pairs returned": len(r["rows"]),
            "Last request (UTC)": r["received_at"],
            "Error": r.get("error") or "",
        }
        for r in results
    ]
    st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)

    if failed:
        st.warning("One or more exchanges failed. Results below use only successful responses.")
        for result in failed:
            st.caption(f'{result["exchange"].upper()}: {result.get("error") or "Unavailable"}')

    st.subheader("Observed market quotes")
    quote_rows = []
    now = datetime.now(timezone.utc)
    for row in all_rows:
        age_seconds = None
        if row.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                age_seconds = (now - timestamp).total_seconds()
            except ValueError:
                pass
        quote_rows.append({
            "Exchange": row["exchange"].upper(),
            "Pair": row["symbol"],
            "Bid": row.get("bid"),
            "Ask": row.get("ask"),
            "Last": row.get("last"),
            "24h Quote Volume": row.get("quote_volume"),
            "Quote age (seconds)": round(age_seconds, 1) if age_seconds is not None else None,
            "Taker fee metadata": row.get("taker_fee"),
        })
    st.dataframe(pd.DataFrame(quote_rows), use_container_width=True, hide_index=True)

    st.subheader("Cross-exchange spread observations")
    if not opportunities:
        st.info("No valid cross-exchange bid/ask comparisons were returned for the selected pairs.")
    else:
        opportunity_rows = []
        for item in opportunities:
            freshest_age = None
            timestamps = [item.get("buy_timestamp"), item.get("sell_timestamp")]
            parsed = []
            for value in timestamps:
                if value:
                    try:
                        parsed.append(datetime.fromisoformat(value.replace("Z", "+00:00")))
                    except ValueError:
                        pass
            if len(parsed) == 2:
                freshest_age = max(0.0, (now - min(parsed)).total_seconds())
            is_fresh = freshest_age is not None and freshest_age <= MAX_DATA_AGE_SECONDS
            opportunity_rows.append({
                "Pair": item["symbol"],
                "Buy venue": item["buy_exchange"].upper(),
                "Buy ask": item["buy_ask"],
                "Sell venue": item["sell_exchange"].upper(),
                "Sell bid": item["sell_bid"],
                "Gross spread %": item["gross_spread_pct"],
                "Estimated net %": item["net_pct"],
                "Quote age (seconds)": round(freshest_age, 1) if freshest_age is not None else None,
                "Fresh quote": is_fresh,
                "Fee basis": item["fee_basis"],
            })
        frame = pd.DataFrame(opportunity_rows)
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.caption(
            "These are observed bid/ask spread comparisons, not confirmed executable arbitrage. "
            "Net estimates use public market fee metadata where available and exclude account-specific "
            "discounts, transfer costs, inventory costs, latency, market impact and partial-fill risk."
        )

st.divider()
st.caption(
    f"Last successful collection attempt: "
    f"{st.session_state.last_fetch.isoformat() if st.session_state.last_fetch else 'Not yet collected'} · "
    "All timestamps UTC."
)
st.caption("ARBIS does not place orders. No fabricated or seeded market values are used.")
