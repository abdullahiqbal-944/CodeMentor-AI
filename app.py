"""
CodeMentor AI
=============
A Generative AI-powered programming mentor built with Gradio + Groq.

Features:
    1. Interactive Code & Logic Explainer
    2. Bug Detector & Optimizer
    3. Progressive Hint Engine (Socratic Mode)
    4. Multi-Language Translator
    5. Automated Unit Test Generator
    6. Complexity Analyzer

Run locally:
    pip install -r requirements.txt
    export GROQ_API_KEY="your_key_here"   # or use the sidebar input
    python app.py
"""

import os
import time
import traceback
from typing import Generator, Optional

import gradio as gr
from dotenv import load_dotenv
from groq import Groq, APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

load_dotenv()  # Loads GROQ_API_KEY from a local .env file if present

DEFAULT_MODEL = "llama-3.3-70b-versatile"

AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

SUPPORTED_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C", "C#",
    "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "SQL",
]

TEST_FRAMEWORKS = {
    "Python": ["pytest", "unittest"],
    "JavaScript": ["Jest", "Mocha"],
    "TypeScript": ["Jest", "Mocha"],
    "Java": ["JUnit 5"],
    "C++": ["Google Test (gtest)"],
    "C#": ["xUnit", "NUnit"],
    "Go": ["testing (stdlib)"],
    "Rust": ["built-in #[test]"],
    "Ruby": ["RSpec"],
    "PHP": ["PHPUnit"],
}

REQUEST_TIMEOUT_SECONDS = 60
MAX_TOKENS_DEFAULT = 4096

# --------------------------------------------------------------------------- #
# Groq client handling
# --------------------------------------------------------------------------- #


def get_client(api_key_override: Optional[str] = None) -> Groq:
    """
    Build a Groq client. Priority:
        1. Explicit key typed into the sidebar (api_key_override)
        2. GROQ_API_KEY environment variable / .env file
    Raises a ValueError with a friendly message if no key is available.
    """
    key = (api_key_override or "").strip() or os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "No Groq API key found. Paste your key into the sidebar field, "
            "or set the GROQ_API_KEY environment variable / .env file."
        )
    return Groq(api_key=key, timeout=REQUEST_TIMEOUT_SECONDS)


def call_groq(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = MAX_TOKENS_DEFAULT,
) -> str:
    """
    Send a chat completion request to Groq and return the text response.
    All expected failure modes are converted into readable strings prefixed
    with an emoji so they render cleanly inside the Gradio Markdown/Code boxes.
    """
    try:
        client = get_client(api_key)
    except ValueError as e:
        return f"⚠️ **Configuration error:** {e}"

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = completion.choices[0].message.content
        return content.strip() if content else "⚠️ The model returned an empty response. Try again."

    except AuthenticationError:
        return (
            "🔑 **Authentication failed.** Your Groq API key appears to be invalid. "
            "Double-check the key in the sidebar or your environment variable."
        )
    except RateLimitError:
        return (
            "🚦 **Rate limit reached.** You've hit Groq's request/token limit for now. "
            "Wait a moment and try again, or switch to a smaller model."
        )
    except APITimeoutError:
        return (
            f"⏱️ **Request timed out** after {REQUEST_TIMEOUT_SECONDS}s. "
            "The Groq API may be under heavy load — please try again."
        )
    except APIConnectionError:
        return (
            "🌐 **Connection error.** Could not reach the Groq API. "
            "Check your internet connection and try again."
        )
    except APIStatusError as e:
        return f"❌ **Groq API error** (status {e.status_code}): {e.message}"
    except Exception:
        return "❌ **Unexpected error:**\n```\n" + traceback.format_exc(limit=2) + "\n```"


# --------------------------------------------------------------------------- #
# Feature 1: Interactive Code & Logic Explainer
# --------------------------------------------------------------------------- #

EXPLAINER_SYSTEM_PROMPT = """You are CodeMentor AI, an expert, patient programming tutor.
Your job is to explain code or programming problems clearly to beginner/intermediate developers.

Structure your answer with Markdown using these sections:
### 🧠 High-Level Summary
A 2-4 sentence plain-English overview of what the code/problem does or asks.

### 🔍 Line-by-Line / Step-by-Step Breakdown
Walk through the logic in the order it executes. Use a numbered list or code-commented style.
If the input is a problem description (no code), instead walk through the reasoning/approach
step by step as if designing the solution.

### 💡 Key Concepts
Bullet list of the core programming concepts, data structures, or algorithms involved,
each with a one-line explanation suitable for someone learning them for the first time.

### ⚠️ Common Pitfalls
Bullet list of mistakes beginners typically make with this kind of code/problem.

Be encouraging, precise, and avoid unnecessary jargon. Use code blocks with correct language
fences for any code you reference."""


def explain_code(api_key, model, language, code_input, depth):
    if not code_input or not code_input.strip():
        return "⚠️ Please paste some code or describe a problem to explain."

    depth_instruction = {
        "Beginner (very detailed)": "Assume the reader is new to programming. Explain every construct, even basic ones like loops or variables, in simple terms.",
        "Intermediate (balanced)": "Assume the reader knows basic syntax already. Focus on logic flow, design decisions, and any non-obvious constructs.",
        "Advanced (concise)": "Assume the reader is experienced. Be concise, focus only on non-trivial logic, algorithmic choices, and subtle behavior.",
    }.get(depth, "")

    user_prompt = f"""Language context: {language}
Explanation depth: {depth} — {depth_instruction}

Here is the code or problem description to explain:

```{language.lower()}
{code_input}
```
"""
    return call_groq(api_key, model, EXPLAINER_SYSTEM_PROMPT, user_prompt, temperature=0.3)


# --------------------------------------------------------------------------- #
# Feature 2: Bug Detector & Optimizer
# --------------------------------------------------------------------------- #

BUG_DETECTOR_SYSTEM_PROMPT = """You are CodeMentor AI's Bug Detector & Optimizer module.
You perform careful static analysis of code to find:
- Syntax errors
- Logical bugs
- Edge-case vulnerabilities (off-by-one errors, null/None handling, empty inputs, overflow, type mismatches, etc.)
- Performance/efficiency issues

Respond in Markdown with EXACTLY these sections:

### 🐞 Issues Found
A numbered list. For each issue give: Issue name, Severity (Critical/Major/Minor), Line reference
(if identifiable), and a short explanation of why it's a problem.
If there truly are no issues, say so explicitly and briefly explain why the code is sound.

### ✅ Corrected Code
A single fenced code block containing the FULL corrected version of the code with the fixes applied.
Preserve the original language and formatting style as much as possible.

### 🛠️ Explanation of Fixes
A bullet list mapping each fix back to the issue it resolves, and why the new approach is better.

### 🚀 Optimization Notes
Bullet list of any performance/readability improvements made or suggested, including complexity
before/after if relevant."""


def detect_bugs(api_key, model, language, code_input, strictness):
    if not code_input or not code_input.strip():
        return "⚠️ Please paste a code snippet to analyze."

    strictness_instruction = {
        "Standard": "Focus on real bugs and meaningful improvements.",
        "Strict (nitpicky)": "Be thorough — flag style inconsistencies, unclear naming, missing docstrings/type hints, and minor edge cases too, in addition to real bugs.",
    }.get(strictness, "")

    user_prompt = f"""Language: {language}
Strictness level: {strictness} — {strictness_instruction}

Analyze this code:

```{language.lower()}
{code_input}
```
"""
    return call_groq(api_key, model, BUG_DETECTOR_SYSTEM_PROMPT, user_prompt, temperature=0.2)


# --------------------------------------------------------------------------- #
# Feature 3: Progressive Hint Engine (Socratic Mode)
# --------------------------------------------------------------------------- #

HINT_SYSTEM_PROMPT = """You are CodeMentor AI's Socratic Hint Engine. Your goal is to help users
learn to solve programming problems THEMSELVES rather than handing them the answer immediately.

Given a problem description (and optionally the user's current attempt/code), produce EXACTLY
three progressive hints using this Markdown structure:

### 🌱 Hint 1 — Conceptual Approach
Describe, in plain English and WITHOUT any code, the general strategy, algorithm family, or
mental model the user should consider (e.g. "think about using a hash map to track seen values").
Do not reveal implementation details yet.

### 🧩 Hint 2 — Structural Clue / Pseudocode
Provide language-agnostic pseudocode or a structural outline (steps, loop shape, key variables)
that guides the user toward an implementation, without writing real, runnable code in the target
language.

### 🔑 Hint 3 — Near-Solution Snippet
Provide a partial, near-complete code snippet in the requested language with strategic gaps
(e.g. `# TODO: handle the empty list case` or blanks like `____`) that the user must fill in
themselves. This should be close to the answer but NOT a fully working, copy-pasteable solution.

Do not include a fourth section with the full solution. Stay encouraging and pedagogical throughout.
If the user's attempt already reveals a specific bug, you may gently acknowledge it within the hints
without directly fixing it for them."""


def generate_hints(api_key, model, language, problem_description, user_attempt):
    if not problem_description or not problem_description.strip():
        return "⚠️ Please describe the problem you're trying to solve."

    attempt_block = (
        f"\nUser's current attempt (do not simply fix it — guide them via hints):\n```{language.lower()}\n{user_attempt}\n```\n"
        if user_attempt and user_attempt.strip()
        else "\nThe user has not written any code yet.\n"
    )

    user_prompt = f"""Target language: {language}

Problem description:
{problem_description}
{attempt_block}
Provide the three progressive hints as instructed."""
    return call_groq(api_key, model, HINT_SYSTEM_PROMPT, user_prompt, temperature=0.5)


# --------------------------------------------------------------------------- #
# Feature 4: Multi-Language Translator
# --------------------------------------------------------------------------- #

TRANSLATOR_SYSTEM_PROMPT = """You are CodeMentor AI's Multi-Language Code Translator.
You convert code from one programming language to another while preserving behavior AND
adapting to the idiomatic style, standard library, and naming conventions of the TARGET language
(not a literal word-for-word port).

Respond in Markdown with EXACTLY these sections:

### 🔄 Translated Code
A single fenced code block with the complete, idiomatic translation in the target language.

### 📌 Key Adaptation Notes
A bullet list explaining notable differences between the languages that affected the translation
(e.g. memory management, typing system, standard library equivalents, error handling conventions).

### ⚠️ Caveats
Bullet list of anything that could not be translated 1:1, requires external libraries/packages
in the target language, or behaves subtly differently, if applicable. If none, state that clearly."""


def translate_code(api_key, model, source_language, target_language, code_input):
    if not code_input or not code_input.strip():
        return "⚠️ Please paste the code you want to translate."
    if source_language == target_language:
        return "⚠️ Source and target languages are the same — please choose two different languages."

    user_prompt = f"""Translate the following {source_language} code into idiomatic {target_language}.

Source code ({source_language}):
```{source_language.lower()}
{code_input}
```
"""
    return call_groq(api_key, model, TRANSLATOR_SYSTEM_PROMPT, user_prompt, temperature=0.2)


# --------------------------------------------------------------------------- #
# Feature 5: Automated Unit Test Generator
# --------------------------------------------------------------------------- #

TEST_GENERATOR_SYSTEM_PROMPT = """You are CodeMentor AI's Unit Test Generator.
Given a code snippet, generate a comprehensive, ready-to-run test suite.

Respond in Markdown with EXACTLY these sections:

### 🧪 Generated Test Suite
A single fenced code block with the complete test file using the specified framework, including
necessary imports/setup. Tests must be runnable (correct syntax, correct import of the
function/class under test — assume it lives in a module named `solution` unless the code implies
otherwise).

### 📋 Coverage Summary
A bullet list describing what each test (or group of tests) covers: typical cases, boundary
conditions, edge cases (empty input, null/None, zero, negative numbers, large input, duplicate
values, invalid types, etc. as relevant), and error/exception handling.

### ➕ Suggested Additional Cases
Bullet list of any further test scenarios worth adding manually (e.g. ones requiring mocks,
performance/load testing, or integration with external systems) that go beyond the generated suite."""


def generate_tests(api_key, model, language, framework, code_input):
    if not code_input or not code_input.strip():
        return "⚠️ Please paste the code you want tests generated for."

    user_prompt = f"""Language: {language}
Testing framework: {framework}

Generate a comprehensive unit test suite for this code:

```{language.lower()}
{code_input}
```
"""
    return call_groq(api_key, model, TEST_GENERATOR_SYSTEM_PROMPT, user_prompt, temperature=0.3)


def update_framework_choices(language):
    frameworks = TEST_FRAMEWORKS.get(language, ["pytest"])
    return gr.update(choices=frameworks, value=frameworks[0])


# --------------------------------------------------------------------------- #
# Feature 6: Complexity Analyzer
# --------------------------------------------------------------------------- #

COMPLEXITY_SYSTEM_PROMPT = """You are CodeMentor AI's Complexity Analyzer.
You determine the Big-O time and space complexity of code and explain the reasoning clearly.

Respond in Markdown with EXACTLY these sections:

### ⏱️ Time Complexity
State the Big-O time complexity (e.g. O(n log n)). Then explain, referencing specific
loops/recursive calls/library operations in the code, how you arrived at that bound. Mention
best-case, average-case, and worst-case if they differ.

### 💾 Space Complexity
State the Big-O space complexity. Explain what contributes to it (auxiliary data structures,
recursion call stack depth, in-place vs. copy operations, etc.).

### 📊 Visual Execution-Cost Breakdown
Produce a Markdown table with columns: `Code Section | Operation | Cost per call | Times executed | Contribution to total`.
Break the code into its major sections/loops/calls and estimate each row so the reader can see
where the dominant cost comes from.

### 🚀 Optimization Potential
Bullet list of whether a more efficient algorithm/data structure exists, what the improved
complexity would be, and the trade-offs involved (implementation complexity, readability, memory
vs. speed, etc.). If the code is already optimal, state that clearly and explain why."""


def analyze_complexity(api_key, model, language, code_input):
    if not code_input or not code_input.strip():
        return "⚠️ Please paste the code you want analyzed."

    user_prompt = f"""Language: {language}

Analyze the time and space complexity of this code:

```{language.lower()}
{code_input}
```
"""
    return call_groq(api_key, model, COMPLEXITY_SYSTEM_PROMPT, user_prompt, temperature=0.2)


# --------------------------------------------------------------------------- #
# API key validation helper (used by the sidebar "Test Connection" button)
# --------------------------------------------------------------------------- #


def test_api_connection(api_key, model):
    try:
        client = get_client(api_key)
    except ValueError as e:
        return f"⚠️ {e}"

    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: pong"}],
            max_tokens=5,
        )
        return "✅ Connection successful! Your Groq API key is valid and the model is reachable."
    except AuthenticationError:
        return "🔑 Authentication failed — the API key is invalid."
    except RateLimitError:
        return "🚦 Key is valid, but you're currently rate-limited. Try again shortly."
    except APITimeoutError:
        return f"⏱️ Timed out after {REQUEST_TIMEOUT_SECONDS}s while testing the connection."
    except APIConnectionError:
        return "🌐 Could not connect to the Groq API. Check your network."
    except APIStatusError as e:
        return f"❌ Groq API error (status {e.status_code}): {e.message}"
    except Exception as e:
        return f"❌ Unexpected error: {e}"


# --------------------------------------------------------------------------- #
# Gradio UI
# --------------------------------------------------------------------------- #

CUSTOM_CSS = """
#header-title { text-align: center; margin-bottom: 0; }
#header-subtitle { text-align: center; color: #666; margin-top: 0; }
.gr-button-primary { font-weight: 600; }
footer { visibility: hidden; }
"""


def build_app() -> gr.Blocks:
    with gr.Blocks(
        title="CodeMentor AI",
        theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="slate"),
        css=CUSTOM_CSS,
    ) as demo:

        gr.Markdown("# 🤖 CodeMentor AI", elem_id="header-title")
        gr.Markdown(
            "Your Generative AI programming mentor — powered by Groq ⚡",
            elem_id="header-subtitle",
        )

        with gr.Row():
            # ----------------------------------------------------------- #
            # Sidebar
            # ----------------------------------------------------------- #
            with gr.Column(scale=1, min_width=280):
                gr.Markdown("### ⚙️ Settings")

                env_key_present = bool(os.environ.get("GROQ_API_KEY", "").strip())
                api_key_input = gr.Textbox(
                    label="Groq API Key",
                    placeholder=(
                        "Using GROQ_API_KEY from environment ✅"
                        if env_key_present
                        else "Paste your Groq API key (gsk_...)"
                    ),
                    type="password",
                    value="",
                )
                gr.Markdown(
                    "🔒 Your key is only kept in this browser session and sent directly "
                    "to the Groq API — it is never stored on a server.\n\n"
                    "Don't have a key? Get one free at "
                    "[console.groq.com/keys](https://console.groq.com/keys)."
                )

                model_dropdown = gr.Dropdown(
                    label="Model",
                    choices=AVAILABLE_MODELS,
                    value=DEFAULT_MODEL,
                )

                test_conn_btn = gr.Button("🔌 Test Connection", size="sm")
                conn_status = gr.Markdown("")
                test_conn_btn.click(
                    fn=test_api_connection,
                    inputs=[api_key_input, model_dropdown],
                    outputs=conn_status,
                )

                gr.Markdown("---")
                gr.Markdown(
                    "**About**\n\n"
                    "CodeMentor AI combines six focused tools to help you read, fix, "
                    "translate, test, and understand code faster — without losing the "
                    "learning process along the way."
                )

            # ----------------------------------------------------------- #
            # Main tabbed workspace
            # ----------------------------------------------------------- #
            with gr.Column(scale=4):
                with gr.Tabs():

                    # ---- Tab 1: Explainer ---- #
                    with gr.Tab("💡 Code Explainer"):
                        gr.Markdown(
                            "Paste code **or** describe a problem, and get a step-by-step, "
                            "beginner-friendly breakdown."
                        )
                        with gr.Row():
                            exp_language = gr.Dropdown(
                                label="Language",
                                choices=["Auto-detect"] + SUPPORTED_LANGUAGES,
                                value="Auto-detect",
                            )
                            exp_depth = gr.Dropdown(
                                label="Explanation Depth",
                                choices=[
                                    "Beginner (very detailed)",
                                    "Intermediate (balanced)",
                                    "Advanced (concise)",
                                ],
                                value="Intermediate (balanced)",
                            )
                        exp_input = gr.Code(
                            label="Code or Problem Description",
                            language="python",
                            lines=14,
                        )
                        exp_btn = gr.Button("🔍 Explain", variant="primary")
                        exp_output = gr.Markdown(label="Explanation")

                        exp_btn.click(
                            fn=explain_code,
                            inputs=[api_key_input, model_dropdown, exp_language, exp_input, exp_depth],
                            outputs=exp_output,
                        )

                    # ---- Tab 2: Bug Detector & Optimizer ---- #
                    with gr.Tab("🐛 Bug Detector & Optimizer"):
                        gr.Markdown(
                            "Scan your code for syntax errors, logic bugs, edge-case gaps, "
                            "and performance issues — with corrected code returned."
                        )
                        with gr.Row():
                            bug_language = gr.Dropdown(
                                label="Language",
                                choices=SUPPORTED_LANGUAGES,
                                value="Python",
                            )
                            bug_strictness = gr.Dropdown(
                                label="Strictness",
                                choices=["Standard", "Strict (nitpicky)"],
                                value="Standard",
                            )
                        bug_input = gr.Code(label="Code to Analyze", language="python", lines=14)
                        bug_btn = gr.Button("🐞 Find & Fix Bugs", variant="primary")
                        bug_output = gr.Markdown(label="Analysis")

                        bug_btn.click(
                            fn=detect_bugs,
                            inputs=[api_key_input, model_dropdown, bug_language, bug_input, bug_strictness],
                            outputs=bug_output,
                        )

                    # ---- Tab 3: Progressive Hint Engine ---- #
                    with gr.Tab("🎯 Socratic Hints"):
                        gr.Markdown(
                            "Get **3 progressive hints** instead of a direct answer — "
                            "conceptual approach → structural clue → near-solution snippet."
                        )
                        hint_language = gr.Dropdown(
                            label="Target Language",
                            choices=SUPPORTED_LANGUAGES,
                            value="Python",
                        )
                        hint_problem = gr.Textbox(
                            label="Problem Description",
                            placeholder="e.g. Given an array of integers, find two numbers that add up to a target value.",
                            lines=4,
                        )
                        hint_attempt = gr.Code(
                            label="Your Current Attempt (optional)",
                            language="python",
                            lines=8,
                        )
                        hint_btn = gr.Button("🌱 Get Hints", variant="primary")
                        hint_output = gr.Markdown(label="Hints")

                        hint_btn.click(
                            fn=generate_hints,
                            inputs=[api_key_input, model_dropdown, hint_language, hint_problem, hint_attempt],
                            outputs=hint_output,
                        )

                    # ---- Tab 4: Multi-Language Translator ---- #
                    with gr.Tab("🔄 Language Translator"):
                        gr.Markdown("Convert code between languages while keeping it idiomatic.")
                        with gr.Row():
                            trans_source = gr.Dropdown(
                                label="Source Language",
                                choices=SUPPORTED_LANGUAGES,
                                value="Python",
                            )
                            trans_target = gr.Dropdown(
                                label="Target Language",
                                choices=SUPPORTED_LANGUAGES,
                                value="C++",
                            )
                        trans_input = gr.Code(label="Source Code", language="python", lines=14)
                        trans_btn = gr.Button("🔄 Translate", variant="primary")
                        trans_output = gr.Markdown(label="Translation")

                        trans_btn.click(
                            fn=translate_code,
                            inputs=[api_key_input, model_dropdown, trans_source, trans_target, trans_input],
                            outputs=trans_output,
                        )

                    # ---- Tab 5: Unit Test Generator ---- #
                    with gr.Tab("🧪 Unit Test Generator"):
                        gr.Markdown("Generate a comprehensive test suite, including edge cases.")
                        with gr.Row():
                            test_language = gr.Dropdown(
                                label="Language",
                                choices=list(TEST_FRAMEWORKS.keys()),
                                value="Python",
                            )
                            test_framework = gr.Dropdown(
                                label="Testing Framework",
                                choices=TEST_FRAMEWORKS["Python"],
                                value="pytest",
                            )
                        test_language.change(
                            fn=update_framework_choices,
                            inputs=test_language,
                            outputs=test_framework,
                        )
                        test_input = gr.Code(label="Code to Test", language="python", lines=14)
                        test_btn = gr.Button("🧪 Generate Tests", variant="primary")
                        test_output = gr.Markdown(label="Generated Tests")

                        test_btn.click(
                            fn=generate_tests,
                            inputs=[api_key_input, model_dropdown, test_language, test_framework, test_input],
                            outputs=test_output,
                        )

                    # ---- Tab 6: Complexity Analyzer ---- #
                    with gr.Tab("⏱️ Complexity Analyzer"):
                        gr.Markdown("Get Big-O time/space complexity with a visual cost breakdown.")
                        comp_language = gr.Dropdown(
                            label="Language",
                            choices=SUPPORTED_LANGUAGES,
                            value="Python",
                        )
                        comp_input = gr.Code(label="Code to Analyze", language="python", lines=14)
                        comp_btn = gr.Button("⏱️ Analyze Complexity", variant="primary")
                        comp_output = gr.Markdown(label="Complexity Analysis")

                        comp_btn.click(
                            fn=analyze_complexity,
                            inputs=[api_key_input, model_dropdown, comp_language, comp_input],
                            outputs=comp_output,
                        )

        gr.Markdown(
            "---\n"
            "Built with ❤️ using [Gradio](https://gradio.app) and [Groq](https://groq.com). "
            "CodeMentor AI does not store your code or API key."
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.queue(max_size=20).launch(
        server_name=os.environ.get("HOST", "0.0.0.0"),
        server_port=int(os.environ.get("PORT", 7860)),
        share=os.environ.get("GRADIO_SHARE", "false").lower() == "true",
    )
