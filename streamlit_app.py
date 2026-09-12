"""
CodeMentor AI — Streamlit Cloud entry point
============================================
This file exists ONLY for platforms that require a native Streamlit app
(e.g. Streamlit Community Cloud). It does NOT launch Gradio's own web server
(which is what breaks on Streamlit Cloud — see README "Deploying to Streamlit
Cloud" for why). It imports the Groq backend logic from backend.py — a module
with ZERO Gradio dependency — so this file never touches Gradio at all and
cannot break due to a Gradio install issue.

Run locally:
    pip install -r requirements.txt
    export GROQ_API_KEY="your_key_here"
    streamlit run streamlit_app.py

Deploy on Streamlit Cloud:
    Set "Main file path" to streamlit_app.py (NOT app.py) and add GROQ_API_KEY
    under App settings -> Secrets, e.g.:
        GROQ_API_KEY = "gsk_your_real_key_here"
"""

import os

import streamlit as st

from backend import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    SUPPORTED_LANGUAGES,
    TEST_FRAMEWORKS,
    analyze_complexity,
    detect_bugs,
    explain_code,
    generate_hints,
    generate_tests,
    test_api_connection,
    translate_code,
)

# --------------------------------------------------------------------------- #
# Page setup
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="CodeMentor AI",
    page_icon="🤖",
    layout="wide",
)

# Streamlit Cloud secrets show up as environment variables are NOT set
# automatically, so mirror st.secrets into os.environ for anything that
# expects GROQ_API_KEY via the environment (e.g. local .env fallback).
if "GROQ_API_KEY" in st.secrets and not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

st.title("🤖 CodeMentor AI")
st.caption("Your Generative AI programming mentor — powered by Groq ⚡ (Streamlit edition)")

# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.header("⚙️ Settings")

    env_key_present = bool(os.environ.get("GROQ_API_KEY", "").strip())
    api_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder=(
            "Using GROQ_API_KEY from secrets/env ✅" if env_key_present else "Paste your Groq API key (gsk_...)"
        ),
        help="Your key is kept only in this session's memory and sent directly to the Groq API.",
    )

    model = st.selectbox("Model", AVAILABLE_MODELS, index=AVAILABLE_MODELS.index(DEFAULT_MODEL))

    st.markdown(
        "Don't have a key? Get one free at "
        "[console.groq.com/keys](https://console.groq.com/keys)."
    )

    if st.button("🔌 Test Connection", use_container_width=True):
        with st.spinner("Testing connection to Groq..."):
            result = test_api_connection(api_key, model)
        if result.startswith("✅"):
            st.success(result)
        else:
            st.warning(result)

    st.markdown("---")
    st.markdown(
        "**About**\n\n"
        "CodeMentor AI combines six focused tools to help you read, fix, "
        "translate, test, and understand code faster — without losing the "
        "learning process along the way."
    )

# --------------------------------------------------------------------------- #
# Main tabbed workspace
# --------------------------------------------------------------------------- #

(
    tab_explain,
    tab_bugs,
    tab_hints,
    tab_translate,
    tab_tests,
    tab_complexity,
) = st.tabs(
    [
        "💡 Code Explainer",
        "🐛 Bug Detector & Optimizer",
        "🎯 Socratic Hints",
        "🔄 Language Translator",
        "🧪 Unit Test Generator",
        "⏱️ Complexity Analyzer",
    ]
)

# ---- Tab 1: Explainer ---- #
with tab_explain:
    st.markdown(
        "Paste code **or** describe a problem, and get a step-by-step, "
        "beginner-friendly breakdown."
    )
    col1, col2 = st.columns(2)
    with col1:
        exp_language = st.selectbox(
            "Language", ["Auto-detect"] + SUPPORTED_LANGUAGES, key="exp_lang"
        )
    with col2:
        exp_depth = st.selectbox(
            "Explanation Depth",
            ["Beginner (very detailed)", "Intermediate (balanced)", "Advanced (concise)"],
            index=1,
            key="exp_depth",
        )
    exp_input = st.text_area("Code or Problem Description", height=300, key="exp_input")
    if st.button("🔍 Explain", type="primary", key="exp_btn"):
        with st.spinner("Thinking..."):
            result = explain_code(api_key, model, exp_language, exp_input, exp_depth)
        st.markdown(result)

# ---- Tab 2: Bug Detector & Optimizer ---- #
with tab_bugs:
    st.markdown(
        "Scan your code for syntax errors, logic bugs, edge-case gaps, "
        "and performance issues — with corrected code returned."
    )
    col1, col2 = st.columns(2)
    with col1:
        bug_language = st.selectbox("Language", SUPPORTED_LANGUAGES, key="bug_lang")
    with col2:
        bug_strictness = st.selectbox(
            "Strictness", ["Standard", "Strict (nitpicky)"], key="bug_strictness"
        )
    bug_input = st.text_area("Code to Analyze", height=300, key="bug_input")
    if st.button("🐞 Find & Fix Bugs", type="primary", key="bug_btn"):
        with st.spinner("Analyzing..."):
            result = detect_bugs(api_key, model, bug_language, bug_input, bug_strictness)
        st.markdown(result)

# ---- Tab 3: Progressive Hint Engine ---- #
with tab_hints:
    st.markdown(
        "Get **3 progressive hints** instead of a direct answer — "
        "conceptual approach → structural clue → near-solution snippet."
    )
    hint_language = st.selectbox("Target Language", SUPPORTED_LANGUAGES, key="hint_lang")
    hint_problem = st.text_area(
        "Problem Description",
        height=120,
        placeholder="e.g. Given an array of integers, find two numbers that add up to a target value.",
        key="hint_problem",
    )
    hint_attempt = st.text_area("Your Current Attempt (optional)", height=200, key="hint_attempt")
    if st.button("🌱 Get Hints", type="primary", key="hint_btn"):
        with st.spinner("Preparing hints..."):
            result = generate_hints(api_key, model, hint_language, hint_problem, hint_attempt)
        st.markdown(result)

# ---- Tab 4: Multi-Language Translator ---- #
with tab_translate:
    st.markdown("Convert code between languages while keeping it idiomatic.")
    col1, col2 = st.columns(2)
    with col1:
        trans_source = st.selectbox("Source Language", SUPPORTED_LANGUAGES, index=0, key="trans_src")
    with col2:
        default_target_idx = SUPPORTED_LANGUAGES.index("C++") if "C++" in SUPPORTED_LANGUAGES else 1
        trans_target = st.selectbox(
            "Target Language", SUPPORTED_LANGUAGES, index=default_target_idx, key="trans_tgt"
        )
    trans_input = st.text_area("Source Code", height=300, key="trans_input")
    if st.button("🔄 Translate", type="primary", key="trans_btn"):
        with st.spinner("Translating..."):
            result = translate_code(api_key, model, trans_source, trans_target, trans_input)
        st.markdown(result)

# ---- Tab 5: Unit Test Generator ---- #
with tab_tests:
    st.markdown("Generate a comprehensive test suite, including edge cases.")
    col1, col2 = st.columns(2)
    with col1:
        test_language = st.selectbox("Language", list(TEST_FRAMEWORKS.keys()), key="test_lang")
    with col2:
        test_framework = st.selectbox(
            "Testing Framework",
            TEST_FRAMEWORKS[test_language],
            key=f"test_framework_{test_language}",
        )
    test_input = st.text_area("Code to Test", height=300, key="test_input")
    if st.button("🧪 Generate Tests", type="primary", key="test_btn"):
        with st.spinner("Writing tests..."):
            result = generate_tests(api_key, model, test_language, test_framework, test_input)
        st.markdown(result)

# ---- Tab 6: Complexity Analyzer ---- #
with tab_complexity:
    st.markdown("Get Big-O time/space complexity with a visual cost breakdown.")
    comp_language = st.selectbox("Language", SUPPORTED_LANGUAGES, key="comp_lang")
    comp_input = st.text_area("Code to Analyze", height=300, key="comp_input")
    if st.button("⏱️ Analyze Complexity", type="primary", key="comp_btn"):
        with st.spinner("Analyzing complexity..."):
            result = analyze_complexity(api_key, model, comp_language, comp_input)
        st.markdown(result)

st.markdown("---")
st.caption(
    "Built with ❤️ using Streamlit and Groq. CodeMentor AI does not store your code or API key."
)
