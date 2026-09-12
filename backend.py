"""
CodeMentor AI — Backend
========================
All Groq API logic and prompt engineering for CodeMentor AI's six features,
completely independent of any UI framework.

Deliberately has NO dependency on Gradio or Streamlit — only `groq` and
`python-dotenv`. Both app.py (Gradio) and streamlit_app.py (Streamlit) import
from this module, so backend logic is written exactly once and each UI stays
usable even if the other UI framework fails to install.

Features:
    1. Interactive Code & Logic Explainer  -> explain_code()
    2. Bug Detector & Optimizer            -> detect_bugs()
    3. Progressive Hint Engine (Socratic)  -> generate_hints()
    4. Multi-Language Translator           -> translate_code()
    5. Automated Unit Test Generator       -> generate_tests()
    6. Complexity Analyzer                 -> analyze_complexity()

Also exposes: get_client(), call_groq(), test_api_connection(), and the
shared constants AVAILABLE_MODELS, DEFAULT_MODEL, SUPPORTED_LANGUAGES,
TEST_FRAMEWORKS.
"""

import os
import traceback
from typing import Optional

from dotenv import load_dotenv
from groq import Groq, APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

load_dotenv()  # Loads GROQ_API_KEY from a local .env file if present

DEFAULT_MODEL = "openai/gpt-oss-120b"

# NOTE: Groq periodically deprecates/decommissions models. llama-3.3-70b-versatile,
# llama-3.1-8b-instant, mixtral-8x7b-32768, and gemma2-9b-it (previously used here)
# have all since been retired. If a model in this list starts failing with a
# "model_decommissioned" / not-found style error, check
# https://console.groq.com/docs/models for the current list and
# https://console.groq.com/docs/deprecations for recommended replacements.
AVAILABLE_MODELS = [
    "openai/gpt-oss-120b",   # Production — high-capability, strong reasoning/coding (replaces llama-3.3-70b-versatile)
    "openai/gpt-oss-20b",    # Production — smaller & faster (replaces llama-3.1-8b-instant)
    "qwen/qwen3.6-27b",      # Preview — strong coding benchmarks; preview models can change/disappear without notice
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
        msg = str(e.message or "")
        if e.status_code == 404 or "decommission" in msg.lower() or "does not exist" in msg.lower():
            return (
                f"🚫 **Model unavailable:** `{model}` appears to be decommissioned or unrecognized by Groq "
                f"(status {e.status_code}). Groq periodically retires models — pick a different one from the "
                f"dropdown, or check https://console.groq.com/docs/models for the current list.\n\n"
                f"Raw error: {msg}"
            )
        return f"❌ **Groq API error** (status {e.status_code}): {msg}"
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
        msg = str(e.message or "")
        if e.status_code == 404 or "decommission" in msg.lower() or "does not exist" in msg.lower():
            return (
                f"🚫 Model `{model}` appears to be decommissioned or unrecognized by Groq "
                f"(status {e.status_code}). Pick a different model, or check "
                f"https://console.groq.com/docs/models for the current list."
            )
        return f"❌ Groq API error (status {e.status_code}): {msg}"
    except Exception as e:
        return 
