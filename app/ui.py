"""Streamlit interface for the financial data agent."""
from __future__ import annotations

import streamlit as st

from app import feedback, policy as policy_mod
from app.agent import Answer, ask

st.set_page_config(
    page_title="Financial Data Console",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        --ink: #172126;
        --muted: #5d6b70;
        --paper: #f5f7f4;
        --line: #d5ddd8;
        --navy: #153a4a;
        --mint: #d9eee4;
        --coral: #e66b4f;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        font-family: "IBM Plex Sans", sans-serif;
        color: var(--ink);
    }
    .stApp {
        background:
            linear-gradient(90deg, rgba(21, 58, 74, 0.035) 1px, transparent 1px),
            linear-gradient(rgba(21, 58, 74, 0.035) 1px, transparent 1px),
            var(--paper);
        background-size: 32px 32px;
    }
    [data-testid="stSidebar"] {
        background: var(--navy);
        border-right: 1px solid #0d2b37;
    }
    [data-testid="stSidebar"] * { color: #f4f8f6; }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"] {
        background: #0d2b37;
        border: 1px solid #2a5a70;
        border-radius: 4px;
    }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] input {
        background: transparent;
        color: #ffffff !important;
        font-weight: 600;
    }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] svg {
        fill: #ffffff;
    }
    .brand {
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.78rem;
        letter-spacing: 0;
        color: #a9d6c1;
        margin-bottom: 2.25rem;
    }
    .brand strong {
        display: block;
        color: #ffffff;
        font-family: "IBM Plex Sans", sans-serif;
        font-size: 1.35rem;
        margin-top: 0.35rem;
    }
    .eyebrow {
        font-family: "IBM Plex Mono", monospace;
        color: var(--coral);
        font-size: 0.78rem;
        text-transform: uppercase;
        margin-bottom: 0.45rem;
    }
    .console-title {
        color: var(--ink);
        font-size: clamp(2rem, 4vw, 3.4rem);
        font-weight: 600;
        line-height: 1.05;
        margin: 0 0 0.7rem;
        letter-spacing: 0;
    }
    .status-line {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: 1rem 0 2rem;
    }
    .status-chip {
        border: 1px solid var(--line);
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.72);
        color: var(--muted);
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.72rem;
        padding: 0.35rem 0.55rem;
    }
    .answer-label {
        border-left: 4px solid var(--coral);
        color: var(--muted);
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.75rem;
        margin-top: 1.8rem;
        padding-left: 0.65rem;
        text-transform: uppercase;
    }
    .source-row {
        border-bottom: 1px solid var(--line);
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.76rem;
        padding: 0.55rem 0;
        overflow-wrap: anywhere;
    }
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 1.1rem;
    }
    .stButton > button, .stFormSubmitButton > button {
        border-radius: 4px;
        font-weight: 600;
    }
    .stFormSubmitButton > button {
        background: var(--coral);
        border-color: var(--coral);
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _render_sidebar() -> tuple[str, object]:
    with st.sidebar:
        st.markdown(
            '<div class="brand">APPLE DATA SYSTEMS<strong>Ledger Console</strong></div>',
            unsafe_allow_html=True,
        )
        role = st.selectbox("Active role", policy_mod.roles(), index=0)
        policy = policy_mod.load(role)
        st.caption(policy.description)
        st.divider()
        st.markdown("**Permitted labels**")
        for label in sorted(policy.allowed_labels):
            st.text(label)
        denied = policy.denied_labels()
        if denied:
            st.markdown("**Withheld labels**")
            for label in denied:
                st.text(label)
        st.divider()
        st.caption("DEMO IDENTITY · ROLE FLAG")
    return role, policy


def _answer_state() -> dict | None:
    value = st.session_state.get("last_answer")
    return value if isinstance(value, dict) else None


role, policy = _render_sidebar()

main_left, main_right = st.columns([4, 1], gap="large")
with main_left:
    st.markdown('<div class="eyebrow">Policy-bound intelligence</div>',
                unsafe_allow_html=True)
    st.markdown('<h1 class="console-title">Financial Data Console</h1>',
                unsafe_allow_html=True)
with main_right:
    st.metric("Active role", role)

st.markdown(
    """
    <div class="status-line">
        <span class="status-chip">PDF + XLSX</span>
        <span class="status-chip">LOCAL EMBEDDINGS</span>
        <span class="status-chip">DATA-LAYER RBAC</span>
        <span class="status-chip">CITED ANSWERS</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("question_form", clear_on_submit=False):
    question = st.text_area(
        "Question",
        placeholder="What were Apple's FY2025 net sales?",
        height=108,
    )
    submitted = st.form_submit_button("Analyze", use_container_width=True)

if submitted:
    clean_question = question.strip()
    if not clean_question:
        st.warning("Enter a question before analyzing.")
    else:
        try:
            with st.spinner("Retrieving permitted sources..."):
                result = ask(clean_question, policy)
            st.session_state["last_answer"] = {
                "question": clean_question,
                "role": role,
                "result": result,
                "rated": False,
            }
        except Exception as exc:
            st.error(f"The request failed: {exc}")

notice = st.session_state.pop("feedback_notice", None)
if notice:
    st.success(notice)

answer_state = _answer_state()
if answer_state:
    result = answer_state["result"]
    if isinstance(result, Answer):
        st.markdown(
            f'<div class="answer-label">Answer · {answer_state["role"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(result.text)

        metric_columns = st.columns(3)
        metric_columns[0].metric("Sources", len(set(result.citations)))
        metric_columns[1].metric("Tool calls", len(result.tools_used))
        metric_columns[2].metric("Withheld", len(result.withheld))

        if result.withheld:
            st.warning("Withheld for this role: " + ", ".join(result.withheld))

        with st.expander("Retrieved source IDs", expanded=False):
            if result.citations:
                for chunk_id in sorted(set(result.citations)):
                    st.markdown(
                        f'<div class="source-row">{chunk_id}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No document chunks were cited.")

        st.markdown("**Rate this retrieval**")
        helpful, unhelpful, spacer = st.columns([1, 1, 4])
        is_rated = bool(answer_state["rated"])

        def save_vote(vote: int) -> None:
            count = feedback.record(
                answer_state["question"],
                answer_state["role"],
                result.citations,
                vote,
            )
            answer_state["rated"] = True
            st.session_state["last_answer"] = answer_state
            st.session_state["feedback_notice"] = (
                f"Feedback recorded for {count} source chunk(s)."
            )
            st.rerun()

        if helpful.button("Helpful", disabled=is_rated,
                          use_container_width=True):
            save_vote(1)
        if unhelpful.button("Not helpful", disabled=is_rated,
                            use_container_width=True):
            save_vote(-1)