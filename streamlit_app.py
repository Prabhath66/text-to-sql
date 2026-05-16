
# streamlit_app.py — Streamlit frontend for QueryMind Text-to-SQL Assistant.
# Run: streamlit run streamlit_app.py  (FastAPI must be on port 8000)

import requests
import pandas as pd
import plotly.express as px
import streamlit as st

API = "http://localhost:8000"

st.set_page_config(
    page_title="QueryMind — Text-to-SQL",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# Fixes: white topbar, dim text, broken upload zone, tab visibility,
#        subheading contrast, sidebar file uploader background
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #0d1117 !important;
    color: #e2e8f0 !important;
}
.stApp { background-color: #0d1117 !important; }

/* ══════════════════════════════════════════════════════
   TOPBAR — tall, branded, with Deploy button styled
   ══════════════════════════════════════════════════════ */
header[data-testid="stHeader"] {
    background: linear-gradient(90deg, #161b27 0%, #1a2035 100%) !important;
    border-bottom: 1px solid #2d3a52 !important;
    height: 3.5rem !important;
    display: flex !important;
    align-items: center !important;
    padding: 0 1.5rem !important;
    box-shadow: 0 1px 8px rgba(0,0,0,0.4) !important;
}

/* Brand text injected via ::before */
header[data-testid="stHeader"]::before {
    content: "🔍  QueryMind  ·  NL → SQL  ·  Powered by Gemini";
    font-family: 'Inter', sans-serif;
    font-size: 0.92rem;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: -0.2px;
    flex: 1;
}

/* Deploy button — style it to match the dark theme */
header[data-testid="stHeader"] button[kind="header"],
header[data-testid="stHeader"] [data-testid="stToolbar"] button,
header[data-testid="stHeader"] .stDeployButton,
[data-testid="stToolbar"] {
    background-color: transparent !important;
    color: #94a3b8 !important;
}
[data-testid="stToolbar"] button {
    background-color: #1c2333 !important;
    color: #94a3b8 !important;
    border: 1px solid #2d3a52 !important;
    border-radius: 6px !important;
    font-size: 0.78rem !important;
    padding: 0.3rem 0.8rem !important;
    transition: all 0.15s !important;
}
[data-testid="stToolbar"] button:hover {
    background-color: #253047 !important;
    color: #e2e8f0 !important;
    border-color: #3b82f6 !important;
}
/* Three-dot menu icon beside Deploy */
[data-testid="stToolbar"] svg { fill: #64748b !important; }
[data-testid="stToolbar"] [data-testid="stToolbarActionButtonIcon"] svg {
    fill: #94a3b8 !important;
    width: 1.1rem !important;
    height: 1.1rem !important;
}

/* Push main content down to clear the taller header */
.main .block-container {
    padding-top: 1.5rem !important;
}

/* ── Hide footer ── */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #161b27 !important;
    border-right: 1px solid #21293d !important;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #e2e8f0 !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    margin-bottom: 0.4rem !important;
}
[data-testid="stSidebar"] .stCaption { color: #94a3b8 !important; }

/* ── Fix file uploader white background in sidebar ── */
[data-testid="stFileUploader"] {
    background-color: #1c2333 !important;
    border: 1px dashed #2d3a52 !important;
    border-radius: 8px !important;
    padding: 0.5rem !important;
}
[data-testid="stFileUploader"] * { color: #94a3b8 !important; }
[data-testid="stFileUploader"] section {
    background-color: #1c2333 !important;
    border: none !important;
}
[data-testid="stFileUploader"] button {
    background-color: #253047 !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d3a52 !important;
    border-radius: 6px !important;
}

/* ── Buttons ── */
.stButton > button {
    background-color: #1c2333 !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d3a52 !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.45rem 1rem !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background-color: #253047 !important;
    border-color: #3b82f6 !important;
    color: #93c5fd !important;
}
.stButton > button[kind="primary"] {
    background-color: #3b82f6 !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #2563eb !important;
    box-shadow: 0 4px 12px rgba(59,130,246,0.35) !important;
}

/* ══════════════════════════════════════════════════════
   DELETE BUTTON — red, compact, vertically aligned
   ══════════════════════════════════════════════════════ */
.delete-btn-col .stButton > button {
    background-color: rgba(239,68,68,0.1) !important;
    color: #ef4444 !important;
    border: 1px solid rgba(239,68,68,0.35) !important;
    border-radius: 6px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 0.35rem 0.7rem !important;
    width: 100% !important;
    margin-top: 0.25rem !important;
}
.delete-btn-col .stButton > button:hover {
    background-color: rgba(239,68,68,0.2) !important;
    border-color: #ef4444 !important;
    color: #fca5a5 !important;
}

/* ── Inputs & textareas ── */
.stTextArea textarea, .stTextInput input {
    background-color: #1c2333 !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d3a52 !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important;
    outline: none !important;
}
.stTextArea label, .stTextInput label { color: #94a3b8 !important; font-size: 0.8rem !important; }

/* ── Selectbox ── */
.stSelectbox > div > div {
    background-color: #1c2333 !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d3a52 !important;
    border-radius: 6px !important;
}
.stSelectbox label { color: #94a3b8 !important; font-size: 0.8rem !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #161b27 !important;
    border-bottom: 1px solid #21293d !important;
    padding: 0 0.5rem !important;
    gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #64748b !important;
    background-color: transparent !important;
    border-radius: 6px 6px 0 0 !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.6rem 1.2rem !important;
}
.stTabs [aria-selected="true"] {
    color: #3b82f6 !important;
    background-color: rgba(59,130,246,0.08) !important;
    border-bottom: 2px solid #3b82f6 !important;
    font-weight: 600 !important;
}

/* ── Headings ── */
h1, h2, h3 { color: #e2e8f0 !important; }
.stSubheader { color: #e2e8f0 !important; font-weight: 700 !important; }
p, .stMarkdown p { color: #cbd5e1 !important; }
.stCaption, small { color: #64748b !important; }

/* ── Expanders ── */
[data-testid="stExpander"] {
    background-color: #161b27 !important;
    border: 1px solid #21293d !important;
    border-radius: 8px !important;
    margin-bottom: 6px !important;
}
[data-testid="stExpander"] summary {
    color: #e2e8f0 !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
}
[data-testid="stExpander"] summary:hover { background-color: #1c2333 !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #21293d !important;
    border-radius: 6px !important;
    overflow: hidden !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background-color: #161b27 !important;
    border: 1px solid #21293d !important;
    border-radius: 8px !important;
    padding: 1rem 1.25rem !important;
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    color: #e2e8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.4rem !important;
}

/* ── Divider ── */
hr { border-color: #21293d !important; margin: 1rem 0 !important; }

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 6px !important; }

/* ── Custom boxes ── */
.sql-box {
    background: #0a0f1a;
    border: 1px solid #f59e0b;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.83rem;
    color: #fde68a;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.6;
    margin: 0.75rem 0;
}
.answer-box {
    background: linear-gradient(135deg, #0f2444 0%, #0d1a35 100%);
    border: 1px solid #1e3a5f;
    border-left: 4px solid #3b82f6;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.25rem;
    color: #e2e8f0;
    font-size: 0.95rem;
    line-height: 1.65;
    margin: 0.75rem 0;
}
.blocked-box {
    background: #1a0a0a;
    border: 1px solid #3d1515;
    border-left: 4px solid #ef4444;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.25rem;
    color: #fca5a5;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.83rem;
    line-height: 1.6;
    margin: 0.75rem 0;
}
.explanation-box {
    background: #1c2333;
    border-left: 3px solid #3b82f6;
    border-radius: 0 6px 6px 0;
    padding: 0.75rem 1rem;
    color: #94a3b8;
    font-size: 0.83rem;
    line-height: 1.6;
    margin: 0.5rem 0 0.75rem;
}
.section-header {
    font-size: 1.15rem;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 0.2rem;
}
.section-desc {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 1rem;
    line-height: 1.5;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def api_call(method: str, path: str, **kwargs):
    """Call the FastAPI backend and return parsed JSON, or None on error."""
    try:
        resp = getattr(requests, method)(API + path, **kwargs)
        if resp.status_code == 200:
            return resp.json()
        st.error(f"API error {resp.status_code}: {resp.text[:300]}")
        return None
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Backend not running. Start it: `uvicorn main:app --reload --port 8000`")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None


def render_chart(rows: list, columns: list, chart_type: str, title: str):
    """Render a Plotly chart based on the detected chart type."""
    if not rows or len(columns) < 2:
        return
    df = pd.DataFrame(rows)
    x, y = columns[0], columns[1]
    COLORS = ["#3b82f6", "#8b5cf6", "#06b6d4", "#22c55e", "#f59e0b", "#ef4444"]
    base_layout = dict(
        paper_bgcolor="#0d1117", plot_bgcolor="#161b27",
        font=dict(family="Inter", color="#94a3b8", size=12),
        xaxis=dict(gridcolor="#21293d", zerolinecolor="#21293d"),
        yaxis=dict(gridcolor="#21293d", zerolinecolor="#21293d"),
        margin=dict(t=50, r=20, b=50, l=60),
    )
    try:
        if chart_type == "line":
            fig = px.line(df, x=x, y=y, title=title, template="plotly_dark",
                          color_discrete_sequence=COLORS)
        elif chart_type == "pie":
            fig = px.pie(df, names=x, values=y, title=title, template="plotly_dark",
                         color_discrete_sequence=COLORS)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, title=title, template="plotly_dark",
                             color_discrete_sequence=["#8b5cf6"])
        else:
            fig = px.bar(df, x=x, y=y, title=title, template="plotly_dark",
                         color_discrete_sequence=COLORS)
        fig.update_layout(**base_layout)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Chart rendering failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
defaults = {
    "pending_sql": None,
    "pending_question": None,
    "pending_explanation": None,
    "last_sql": "",
    "question_input": "",
    "exec_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 QueryMind")
    st.caption("Natural Language → SQL · Powered by Gemini")
    st.divider()

    # ── Table browser ──────────────────────────────────────────────────────
    st.markdown("### 🗄️ Database Tables")
    tables_data = api_call("get", "/tables")
    if tables_data:
        all_tables = tables_data.get("tables", {})
        table_names = sorted(all_tables.keys())
        if table_names:
            selected_table = st.selectbox(
                "Select a table to preview",
                ["— choose a table —"] + table_names,
                label_visibility="collapsed",
            )
            if selected_table and selected_table != "— choose a table —":
                sample = api_call("get", f"/sample/{selected_table}")
                if sample and sample.get("rows"):
                    st.dataframe(
                        pd.DataFrame(sample["rows"]),
                        use_container_width=True,
                        height=200,
                    )
                    info = all_tables.get(selected_table, {})
                    src = "uploaded" if info.get("source") == "uploaded" else "base db"
                    st.caption(
                        f"{info.get('row_count', 0):,} rows · "
                        f"{len(info.get('columns', []))} cols · {src}"
                    )
        else:
            st.caption("No tables found.")
    else:
        st.caption("Could not connect to backend.")

    st.divider()

    # ── File upload ────────────────────────────────────────────────────────
    st.markdown("### 📤 Upload Data")
    st.caption("CSV · Excel (.xlsx/.xls) · JSON")
    uploaded_files = st.file_uploader(
        "upload",
        type=["csv", "xlsx", "xls", "json"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploaded_files:
        st.caption(f"{len(uploaded_files)} file(s) ready")
        if st.button("⚡ Load Files", type="primary", use_container_width=True):
            files_payload = [("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files]
            try:
                resp = requests.post(f"{API}/upload", files=files_payload, timeout=30)
                if resp.status_code == 200:
                    created = resp.json().get("tables_created", [])
                    st.success(f"✅ Loaded: {', '.join(created)}")
                    st.rerun()
                else:
                    st.error(f"Upload failed: {resp.text[:200]}")
            except Exception as e:
                st.error(f"Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_ask, tab_schema, tab_validate, tab_translate = st.tabs([
    "💬 Ask Questions", "🗃️ Schema", "🛡️ SQL Validator", "🔄 Dialect Translator"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ASK QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_ask:
    st.markdown('<p class="section-header">Ask a Question About Your Data</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-desc">Type a question in plain English — Gemini will generate the SQL, explain it, and summarise the results.</p>', unsafe_allow_html=True)

    EXAMPLES = [
        "What are the top 5 customers by total order amount?",
        "Show total revenue by product category",
        "How many orders were placed each month in 2024?",
        "Which products have the lowest stock?",
        "What percentage of orders were delivered vs cancelled?",
        "Show me customers who placed more than one order",
    ]

    st.markdown("**Suggested questions** — click to use:")
    ex_cols = st.columns(3)
    for i, ex in enumerate(EXAMPLES):
        with ex_cols[i % 3]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state.question_input = ex
                st.session_state.pending_sql = None
                st.session_state.exec_result = None
                st.rerun()

    st.divider()

    question = st.text_area(
        "Your question",
        value=st.session_state.question_input or "",
        height=90,
        placeholder="e.g. Who are the top 5 customers by revenue?",
    )

    btn_col, _ = st.columns([4, 8])
    with btn_col:
        generate_clicked = st.button(
            "🔍 Generate SQL",
            type="primary",
            disabled=not bool(question.strip()),
            use_container_width=True,
        )

    if generate_clicked and question.strip():
        st.session_state.pending_sql = None
        st.session_state.exec_result = None
        with st.spinner("Generating SQL with Gemini…"):
            result = api_call("post", "/query", json={"question": question, "execute": False})
        if result:
            if not result.get("success"):
                st.markdown(
                    f'<div class="blocked-box">🚫 <strong>Blocked:</strong> {result.get("reason", "Unknown error")}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.session_state.pending_sql = result["sql"]
                st.session_state.pending_question = question
                st.session_state.pending_explanation = result.get("sql_explanation", "")
                st.session_state.last_sql = result["sql"]

    # ── SQL Review ────────────────────────────────────────────────────────
    if st.session_state.pending_sql:
        st.divider()
        st.markdown("**Generated SQL — review before running:**")
        st.markdown(
            f'<div class="sql-box">{st.session_state.pending_sql}</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.pending_explanation:
            st.markdown(
                f'<div class="explanation-box">💡 {st.session_state.pending_explanation}</div>',
                unsafe_allow_html=True,
            )

        run_col, cancel_col, _ = st.columns([3, 3, 7])
        with run_col:
            run_clicked = st.button("▶ Run Query", type="primary", use_container_width=True)
        with cancel_col:
            if st.button("✕ Cancel", use_container_width=True):
                st.session_state.pending_sql = None
                st.session_state.pending_explanation = None
                st.rerun()

        if run_clicked:
            q = st.session_state.pending_question
            with st.spinner("Executing query…"):
                exec_result = api_call("post", "/query", json={"question": q, "execute": True})
            st.session_state.pending_sql = None
            st.session_state.exec_result = exec_result

    # ── Results ───────────────────────────────────────────────────────────
    if st.session_state.exec_result:
        er = st.session_state.exec_result
        if not er.get("success"):
            st.markdown(
                f'<div class="blocked-box">🚫 <strong>Error:</strong> {er.get("reason", "Unknown")}</div>',
                unsafe_allow_html=True,
            )
        else:
            if er.get("answer"):
                st.markdown(
                    f'<div class="answer-box">💬 {er["answer"]}</div>',
                    unsafe_allow_html=True,
                )

            m1, m2, m3 = st.columns(3)
            m1.metric("Rows Returned", er.get("row_count", 0))
            m2.metric("Columns", len(er.get("columns", [])))
            m3.metric("Chart Type", er.get("chart_type", "bar").capitalize())

            rows = er.get("rows", [])
            columns = er.get("columns", [])

            if rows and len(columns) >= 2:
                render_chart(rows, columns, er.get("chart_type", "bar"),
                             st.session_state.pending_question or "")

            if rows:
                with st.expander("📊 Full Results Table", expanded=True):
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode()
                    st.download_button("⬇️ Download CSV", csv, "results.csv", "text/csv")

            with st.expander("🔍 SQL Executed"):
                st.code(er.get("sql", ""), language="sql")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SCHEMA
# ══════════════════════════════════════════════════════════════════════════════
with tab_schema:
    st.markdown('<p class="section-header">Schema Explorer</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-desc">Browse column definitions for all tables. Uploaded tables can be deleted.</p>', unsafe_allow_html=True)

    ref_col, _ = st.columns([6, 9])
    with ref_col:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    schema_data = api_call("get", "/schema")
    if schema_data:
        base = schema_data.get("base_tables", {})
        uploaded = schema_data.get("uploaded_tables", {})

        if base:
            st.markdown("#### 🗃️ Database Tables")
            for tname, info in base.items():
                with st.expander(
                    f"**{tname}**  ·  {info['row_count']:,} rows  ·  {len(info['columns'])} columns"
                ):
                    st.dataframe(
                        pd.DataFrame(info["columns"]),
                        hide_index=True,
                        use_container_width=True,
                    )

        if uploaded:
            st.markdown("#### 📤 Uploaded Tables")
            for tname, info in uploaded.items():
                exp_col, del_col = st.columns([7, 1])
                with exp_col:
                    with st.expander(
                        f"**{tname}**  ·  {info['row_count']:,} rows  ·  source: `{info.get('source_file', '')}`"
                    ):
                        st.dataframe(
                            pd.DataFrame(info["columns"]),
                            hide_index=True,
                            use_container_width=True,
                        )
                with del_col:
                    st.write("")
                    # Wrap in a div so the .delete-btn-col CSS class applies
                    st.markdown('<div class="delete-btn-col">', unsafe_allow_html=True)
                    if st.button("🗑️ Delete", key=f"del_{tname}", help=f"Permanently delete '{tname}'"):
                        resp = requests.delete(f"{API}/tables/{tname}")
                        if resp.status_code == 200:
                            st.success(f"Deleted '{tname}'")
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Delete failed"))
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No uploaded tables yet. Use the sidebar to upload CSV / Excel / JSON files.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SQL VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_validate:
    st.markdown('<p class="section-header">SQL Safety Validator</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-desc">Checks that your SQL is read-only (SELECT / WITH only) with no write or DDL keywords.</p>', unsafe_allow_html=True)

    default_sql = st.session_state.last_sql or "SELECT * FROM customers LIMIT 10;"
    sql_input = st.text_area(
        "SQL to validate",
        value=default_sql,
        height=160,
        key="validate_input",
        label_visibility="collapsed",
    )

    val_col, _ = st.columns([2, 8])
    with val_col:
        if st.button("🛡️ Check Safety", type="primary", use_container_width=True):
            result = api_call("post", "/validate", json={"sql": sql_input})
            if result:
                if result["safe"]:
                    st.success(f"✅ Safe — {result['reason']}")
                else:
                    st.error(f"🚫 Blocked — {result['reason']}")
                st.markdown("**Cleaned SQL:**")
                st.code(result["cleaned_sql"], language="sql")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DIALECT TRANSLATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_translate:
    st.markdown('<p class="section-header">SQL Dialect Translator</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-desc">Translate a SQLite query to MySQL, PostgreSQL, SQL Server, Oracle, BigQuery, or Snowflake using Gemini.</p>', unsafe_allow_html=True)

    dialects = ["MySQL", "PostgreSQL", "SQL Server", "Oracle", "BigQuery", "Snowflake"]

    default_sql_t = st.session_state.last_sql or (
        "SELECT strftime('%Y-%m', order_date) AS month,\n"
        "       SUM(total_amount) AS revenue\n"
        "FROM orders\n"
        "GROUP BY month\n"
        "ORDER BY month;"
    )

    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.markdown("**SQLite Query (input)**")
        sql_to_translate = st.text_area(
            "sql_translate",
            value=default_sql_t,
            height=220,
            label_visibility="collapsed",
            key="translate_input",
        )

    with right_col:
        st.markdown("**Target Dialect**")
        target = st.selectbox(
            "dialect",
            dialects,
            index=1,
            label_visibility="collapsed",
        )
        st.write("")
        translate_clicked = st.button("🔄 Translate", type="primary", use_container_width=True)

    if translate_clicked:
        with st.spinner(f"Translating to {target}…"):
            result = api_call("post", "/translate", json={"sql": sql_to_translate, "dialect": target})
        if result:
            translated = result.get("translated_sql", "")
            notes = result.get("notes", "")
            st.divider()
            st.markdown(f"**Translated SQL → {target}:**")
            st.code(translated, language="sql")
            if notes and notes.strip() not in ("No changes needed", ""):
                st.info(f"📝 Changes made:\n{notes}")
            if translated:
                dl_col, _ = st.columns([2, 8])
                with dl_col:
                    st.download_button(
                        f"⬇️ Download {target}.sql",
                        translated.encode(),
                        f"query_{target.lower().replace(' ', '_')}.sql",
                        "text/plain",
                        use_container_width=True,
                    )
