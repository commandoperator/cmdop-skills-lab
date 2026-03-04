"""Reusable Streamlit chart components for the email dashboard."""

import pandas as pd
import streamlit as st


def render_metrics(stats: dict) -> None:
    """Render 4 metric cards in columns."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sent", stats["total"])
    c2.metric("Today", stats["today"])
    c3.metric("This Week", stats["week"])
    c4.metric("Errors", stats["errors"])


def render_timeline(df: pd.DataFrame) -> None:
    """Bar chart of emails sent per day."""
    if df.empty:
        st.info("No data for timeline.")
        return
    daily = (
        df.assign(date=df["sent_at"].dt.date)
        .groupby("date")
        .size()
        .to_frame("count")
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    st.bar_chart(daily, x="date", y="count")


def render_top_recipients(df: pd.DataFrame) -> None:
    """Horizontal bar chart of top recipients."""
    if df.empty:
        st.info("No recipient data.")
        return
    st.bar_chart(df, x="to_addr", y="count", horizontal=True)


def render_status_pie(df: pd.DataFrame) -> None:
    """Status breakdown as a simple bar chart (ok vs error)."""
    if df.empty:
        st.info("No data for status breakdown.")
        return
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    st.bar_chart(status_counts, x="status", y="count")
