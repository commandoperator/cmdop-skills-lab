# Streamlit Dashboards for CMDOP Skills

How to add a Streamlit dashboard to a CMDOP skill for visual monitoring, data browsing, and analytics.

## When to Use

Add a dashboard when your skill stores data (SQLite, JSON logs) and users benefit from:

- Browsing historical records with filters
- Viewing aggregated metrics and charts
- Searching and inspecting individual entries

Streamlit dashboards are **standalone** — they run separately from the skill via `streamlit run` and do not depend on CMDOP at runtime.

## Directory Layout

Add a `dashboard/` directory inside the skill:

```
my-skill/
├── pyproject.toml
├── skill/
│   ├── config.py
│   └── readme.md
├── src/my_skill/
│   ├── __init__.py
│   └── _skill.py
├── tests/
├── dashboard/                  # Streamlit dashboard (standalone)
│   ├── app.py                  # Entry point
│   ├── db_reader.py            # Sync data access layer
│   ├── charts.py               # Reusable chart components
│   └── requirements.txt        # Dashboard-only deps
└── data/                       # Runtime data (gitignored)
    └── my_skill.db
```

The `dashboard/` directory has its own `requirements.txt`. Keep skill and dashboard dependencies separate.

## The Async Problem

CMDOP skills typically use async libraries (Tortoise ORM, httpx) for database access. Streamlit is **synchronous** — it cannot run `async/await` natively.

Do **not** wrap async calls with `asyncio.run()` inside Streamlit. It causes event loop conflicts.

**Instead**, use `sqlite3` + `pandas` for read-only dashboard access:

```python
# dashboard/db_reader.py
import sqlite3
import pandas as pd

DB_PATH = "/path/to/data.db"

def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)

def get_all_records(limit: int = 500) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM records ORDER BY created_at DESC LIMIT ?",
        conn,
        params=[limit],
    )
    conn.close()
    return df
```

SQLite handles concurrent reads safely, so the dashboard can read while the skill writes.

## Resolving DB_PATH

The dashboard runs in a different context from the skill. Derive `DB_PATH` from the file location:

```python
import os

# dashboard/db_reader.py is at my-skill/dashboard/db_reader.py
# DB is at my-skill/data/my_skill.db
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SKILL_DIR, "data", "my_skill.db")
```

Never hardcode absolute paths. Never duplicate config from the skill package.

## db_reader.py

Keep all SQL queries in one file. Return `pd.DataFrame` for tables/charts and `dict` for scalar metrics.

```python
import os
import sqlite3
import pandas as pd

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SKILL_DIR, "data", "my_skill.db")


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def db_exists() -> bool:
    return os.path.isfile(DB_PATH)


def get_all_records(limit: int = 500) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM records ORDER BY created_at DESC LIMIT ?",
        conn,
        params=[limit],
    )
    conn.close()
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


def get_stats() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM records WHERE status='ok'").fetchone()[0]
    errors = cur.execute("SELECT COUNT(*) FROM records WHERE status='error'").fetchone()[0]
    conn.close()
    return {"total": total, "errors": errors}
```

Rules:

- Always `conn.close()` after each query
- Parse datetime columns with `pd.to_datetime()` after loading
- Include a `db_exists()` helper — the dashboard must handle a missing DB gracefully
- Use parameterized queries (`?` placeholders) — never f-string SQL

## charts.py

Extract chart rendering into functions that accept DataFrames. Keeps `app.py` clean and makes charts testable.

```python
import pandas as pd
import streamlit as st


def render_metrics(stats: dict) -> None:
    cols = st.columns(len(stats))
    for col, (label, value) in zip(cols, stats.items()):
        col.metric(label.replace("_", " ").title(), value)


def render_timeline(df: pd.DataFrame, date_col: str = "created_at") -> None:
    if df.empty:
        st.info("No data for timeline.")
        return
    daily = (
        df.assign(date=df[date_col].dt.date)
        .groupby("date")
        .size()
        .to_frame("count")
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    st.bar_chart(daily, x="date", y="count")


def render_bar(df: pd.DataFrame, x: str, y: str, horizontal: bool = False) -> None:
    if df.empty:
        st.info("No data.")
        return
    st.bar_chart(df, x=x, y=y, horizontal=horizontal)
```

Rules:

- Each function renders exactly one visual element
- Handle empty DataFrames with `st.info()` — never let charts crash
- Accept column names as parameters for generic components
- Use Streamlit built-ins (`st.bar_chart`, `st.line_chart`) for simple charts; add Altair only for custom visuals

## app.py

Standard layout for skill dashboards:

```python
import time
import pandas as pd
import streamlit as st

from db_reader import DB_PATH, db_exists, get_all_records, get_stats
from charts import render_metrics, render_timeline

# --- Page config (must be first st call) ---
st.set_page_config(page_title="My Dashboard", layout="wide")
st.title("My Dashboard")

# --- Sidebar: filters ---
with st.sidebar:
    st.header("Filters")
    date_range = st.date_input("Date range", value=[])
    status_filter = st.multiselect("Status", ["ok", "error"], default=["ok", "error"])
    search = st.text_input("Search")
    st.divider()
    auto_refresh = st.toggle("Auto-refresh", value=False)
    refresh_sec = st.slider("Interval (sec)", 5, 120, 30, disabled=not auto_refresh)

# --- Guard: DB must exist ---
if not db_exists():
    st.warning(f"Database not found at `{DB_PATH}`.")
    st.stop()

# --- Load & filter ---
df = get_all_records(limit=2000)
if df.empty:
    st.info("No records yet.")
    st.stop()

filtered = df.copy()
if status_filter:
    filtered = filtered[filtered["status"].isin(status_filter)]
if search:
    q = search.lower()
    filtered = filtered[filtered["name"].str.lower().str.contains(q, na=False)]

# --- Metrics ---
stats = get_stats()
render_metrics(stats)

# --- Charts ---
st.divider()
render_timeline(filtered)

# --- Data table ---
st.divider()
st.subheader(f"Records ({len(filtered)})")
st.dataframe(filtered, use_container_width=True, hide_index=True)

# --- Footer ---
st.divider()
st.caption(f"DB: `{DB_PATH}` | Total: {len(df)} | Showing: {len(filtered)}")

# --- Auto-refresh ---
if auto_refresh:
    time.sleep(refresh_sec)
    st.rerun()
```

### Key patterns

1. **`st.set_page_config()` must be the first Streamlit call**
2. **Guard with `st.stop()`** — if DB missing or empty, show a message and stop
3. **Load once, filter in memory** — call `get_all_records()` once, filter the DataFrame in Python
4. **Sidebar for filters** — keeps the main area clean
5. **Auto-refresh** — `time.sleep()` + `st.rerun()` is the standard Streamlit polling pattern

## Sidebar Filter Recipes

### Date range

```python
date_range = st.date_input("Date range", value=[])
if date_range:
    dates = list(date_range)
    if len(dates) == 2:
        start = pd.Timestamp(dates[0])
        end = pd.Timestamp(dates[1]) + pd.Timedelta(days=1)
        filtered = filtered[
            (filtered["created_at"] >= start) & (filtered["created_at"] < end)
        ]
```

### Multiselect enum filter

```python
status = st.multiselect("Status", ["ok", "error", "pending"], default=["ok", "error"])
if status:
    filtered = filtered[filtered["status"].isin(status)]
```

### Text search across columns

```python
query = st.text_input("Search")
if query:
    q = query.lower()
    filtered = filtered[
        filtered["subject"].str.lower().str.contains(q, na=False)
        | filtered["recipient"].str.lower().str.contains(q, na=False)
    ]
```

## Expandable Row Details

For tables with long text fields, use an expander:

```python
with st.expander("View details"):
    idx = st.selectbox(
        "Select record",
        range(len(filtered)),
        format_func=lambda i: f"{filtered.iloc[i]['created_at']} — {filtered.iloc[i]['title'][:60]}",
    )
    row = filtered.iloc[idx]
    st.markdown(f"**Title:** {row['title']}")
    st.text_area("Body", value=row["body"], height=200, disabled=True)
    if row.get("error_message"):
        st.error(row["error_message"])
```

## requirements.txt

Dashboard dependencies are minimal:

```
streamlit>=1.40.0
pandas>=2.0.0
```

Do **not** include the skill's own dependencies — the dashboard does not use them.

## Running

```bash
# Install dashboard deps
pip install -r dashboard/requirements.txt

# Launch
cd my-skill
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`. Streamlit auto-reloads on file changes.

Different port:

```bash
streamlit run dashboard/app.py --server.port 8502
```

## Adding a Makefile target

Add to your skill's Makefile:

```makefile
dashboard:
	streamlit run dashboard/app.py
```

## Checklist

When adding a dashboard to a skill:

- [ ] `dashboard/` directory inside the skill
- [ ] `dashboard/requirements.txt` with `streamlit` and `pandas`
- [ ] `dashboard/db_reader.py` — sync SQLite reader, `DB_PATH` derived from `__file__`
- [ ] `dashboard/charts.py` — chart components, each handles empty data
- [ ] `dashboard/app.py` — page config first, guards with `st.stop()`, sidebar filters
- [ ] DB existence guard with helpful message
- [ ] `data/` directory in `.gitignore`
- [ ] Makefile target for `dashboard`
