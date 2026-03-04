"""llm-email Streamlit Dashboard."""

import time

import pandas as pd
import streamlit as st

from llm_email.dashboard.db_reader import DB_PATH, db_exists, get_all_emails, get_stats, get_top_recipients
from llm_email.dashboard.charts import render_metrics, render_timeline, render_top_recipients, render_status_pie


def main() -> None:
    """Entry point for ``llm-email-dashboard`` CLI command."""
    import sys
    from streamlit.web.cli import main as st_main

    sys.argv = ["streamlit", "run", __file__]
    st_main()


if __name__ == "__main__" or st.runtime.exists():
    st.set_page_config(page_title="Email Dashboard", page_icon=":envelope:", layout="wide")
    st.title("Email Dashboard")

    # --- Sidebar ---
    with st.sidebar:
        st.header("Filters")

        date_range = st.date_input("Date range", value=[])

        status_filter = st.multiselect("Status", options=["ok", "error"], default=["ok", "error"])
        action_filter = st.multiselect("Action", options=["send", "draft"], default=["send", "draft"])
        search_query = st.text_input("Search (subject / recipient)")

        st.divider()
        auto_refresh = st.toggle("Auto-refresh", value=False)
        refresh_interval = st.slider("Interval (sec)", 5, 120, 30, disabled=not auto_refresh)

    # --- Guard: DB must exist ---
    if not db_exists():
        st.warning(f"Database not found at `{DB_PATH}`. Send an email first to create it.")
        st.stop()

    # --- Load data ---
    df = get_all_emails(limit=2000)

    if df.empty:
        st.info("No emails recorded yet.")
        st.stop()

    # --- Apply filters ---
    filtered = df.copy()

    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]

    if action_filter:
        filtered = filtered[filtered["action"].isin(action_filter)]

    if search_query:
        q = search_query.lower()
        filtered = filtered[
            filtered["subject"].str.lower().str.contains(q, na=False)
            | filtered["to_addr"].str.lower().str.contains(q, na=False)
        ]

    if date_range:
        dates = list(date_range)
        if len(dates) == 1:
            day = pd.Timestamp(dates[0])
            filtered = filtered[filtered["sent_at"].dt.date == day.date()]
        elif len(dates) == 2:
            start = pd.Timestamp(dates[0])
            end = pd.Timestamp(dates[1]) + pd.Timedelta(days=1)
            filtered = filtered[(filtered["sent_at"] >= start) & (filtered["sent_at"] < end)]

    # --- Row 1: Metrics ---
    stats = get_stats()
    render_metrics(stats)

    st.divider()

    # --- Row 2: Charts ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Sends per Day")
        render_timeline(filtered)

    with col_right:
        st.subheader("Top Recipients")
        top = get_top_recipients(limit=10)
        render_top_recipients(top)

    st.divider()

    # --- Row 3: Status breakdown ---
    col_status, _ = st.columns([1, 2])
    with col_status:
        st.subheader("Status Breakdown")
        render_status_pie(filtered)

    st.divider()

    # --- Row 4: Data table ---
    st.subheader(f"Emails ({len(filtered)} records)")

    display_cols = ["sent_at", "to_addr", "subject", "action", "status", "from_account"]
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "sent_at": st.column_config.DatetimeColumn("Sent At", format="YYYY-MM-DD HH:mm"),
            "to_addr": "Recipient",
            "subject": "Subject",
            "action": "Action",
            "status": "Status",
            "from_account": "From Account",
        },
    )

    # --- Expandable details ---
    with st.expander("View email details"):
        if filtered.empty:
            st.write("No records to display.")
        else:
            selected_idx = st.selectbox(
                "Select email",
                range(len(filtered)),
                format_func=lambda i: f"{filtered.iloc[i]['sent_at']} — {filtered.iloc[i]['subject'][:60]}",
            )
            row = filtered.iloc[selected_idx]
            st.markdown(f"**To:** {row['to_addr']}")
            if row.get("cc_addr"):
                st.markdown(f"**CC:** {row['cc_addr']}")
            if row.get("bcc_addr"):
                st.markdown(f"**BCC:** {row['bcc_addr']}")
            st.markdown(f"**Subject:** {row['subject']}")
            st.markdown(f"**Action:** {row['action']} | **Status:** {row['status']}")
            if row.get("error_message"):
                st.error(f"Error: {row['error_message']}")
            st.text_area("Body", value=row["body"], height=200, disabled=True)

    # --- Footer ---
    st.divider()
    st.caption(f"DB: `{DB_PATH}` | Total records: {len(df)} | Showing: {len(filtered)}")

    # --- Auto-refresh ---
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
