"""Streamlit demo:  streamlit run app/streamlit_app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from advisor.agent import Advisor
from advisor.tools import Profile, convert_cgpa_to_german, load_programs

st.set_page_config(page_title="Germany Program Advisor", page_icon="🎓", layout="wide")


@st.cache_resource
def get_advisor() -> Advisor:
    return Advisor()


adv = get_advisor()

st.title("🎓 Germany Program Advisor")
st.caption("RAG + agent over official master's program pages (TU Munich, RWTH Aachen, Saarland, Tübingen). "
           "Answers are cited. Always verify on the official university page.")

with st.sidebar:
    st.header("Your profile")
    country = st.selectbox("Bachelor's country", ["India", "China", "Vietnam", "Other"], index=0)
    degree = st.text_input("Degree field", "Artificial Intelligence and Machine Learning")
    cgpa = st.number_input("CGPA", 0.0, 10.0, 8.4, 0.1)
    scale = st.number_input("CGPA scale", 4.0, 10.0, 10.0, 0.5)
    gre_q = st.number_input("GRE Quant (0 = none)", 0, 170, 0)
    gre_a = st.number_input("GRE AWA (0 = none)", 0.0, 6.0, 0.0, 0.5)
    english = st.checkbox("English test done", False)
    aps = st.checkbox("APS certificate done", False)
    profile = Profile(country=country, degree_field=degree, cgpa=cgpa, scale=scale,
                      gre_quant=gre_q or None, gre_awa=gre_a or None,
                      english_test_done=english, aps_done=aps)
    conv = convert_cgpa_to_german(cgpa, scale)
    st.metric("Estimated German grade", f"{conv['estimate_low']} to {conv['estimate_high']}")
    st.caption(conv["caveat"])

tab_chat, tab_data = st.tabs(["Ask", "Data sources"])

with tab_chat:
    examples = [
        "Am I eligible for the Tuebingen machine learning master?",
        "What is the TUM Informatics winter deadline and what GRE score do I need?",
        "Which documents do I need for TUM Informatics?",
        "Compare deadlines for Saarland and RWTH Software Systems Engineering",
    ]
    cols = st.columns(len(examples))
    clicked = None
    for col, ex in zip(cols, examples):
        if col.button(ex, use_container_width=True):
            clicked = ex
    question = st.chat_input("Ask about programs, eligibility, deadlines or documents") or clicked
    if "history" not in st.session_state:
        st.session_state.history = []
    if question:
        res = adv.run(question, profile)
        st.session_state.history.append((question, res))
    for q, res in reversed(st.session_state.history):
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.write(res.answer)
            if res.sources:
                with st.expander("Sources"):
                    st.text(res.sources)
            if res.tool_calls:
                with st.expander("Agent trace (tool calls)"):
                    st.json([{"tool": c["tool"], "args": c["args"]} for c in res.tool_calls])
                    st.caption(f"intents: {res.intents} | programs: {res.programs}")

with tab_data:
    st.subheader("Documents in the knowledge base")
    seen = {}
    for c in adv.chunks:
        seen.setdefault(c.doc_id, c)
    st.dataframe([{
        "doc_id": c.doc_id, "university": c.university, "program": c.program,
        "source_type": c.source_type, "status": c.status, "scraped_on": c.scraped_on, "url": c.source_url,
    } for c in seen.values()], use_container_width=True)
    st.caption(f"{len(adv.chunks)} chunks, {len(load_programs())} programs with structured rules.")
