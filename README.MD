# 🤖 CodeMentor AI

**CodeMentor AI** is a Generative AI-powered programming mentor for beginner and
intermediate developers. It runs on the [Groq API](https://groq.com) (using fast
models like `llama-3.3-70b-versatile`) behind a clean, tabbed [Gradio](https://gradio.app)
interface.

## ✨ Features

| Tab | What it does |
|---|---|
| 💡 **Code Explainer** | Step-by-step, line-by-line explanations of code or problem descriptions, adjustable to your skill level. |
| 🐛 **Bug Detector & Optimizer** | Finds syntax errors, logic bugs, and edge-case issues; returns corrected code + explanation. |
| 🎯 **Socratic Hints** | Gives 3 progressive hints (concept → pseudocode → near-solution) instead of the full answer. |
| 🔄 **Language Translator** | Converts code between languages idiomatically (e.g. Python → C++, JS → Rust). |
| 🧪 **Unit Test Generator** | Generates a full test suite (pytest, unittest, Jest, JUnit, etc.) with edge cases. |
| ⏱️ **Complexity Analyzer** | Big-O time & space complexity with a visual execution-cost table. |

---

## 📁 Project Structure

```
codementor-ai/
├── app.py              # Gradio UI + Groq backend logic
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── README.md           # You are here
```

---

## 🚀 Quickstart (Local)

### 1. Clone / download the project

```bash
git clone https://github.com/<your-username>/codementor-ai.git
cd codementor-ai
```

*(If you just downloaded the files directly, skip the clone step and `cd` into the folder instead.)*

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your Groq API key

Get a free API key at **[console.groq.com/keys](https://console.groq.com/keys)**.

Copy the example env file and add your key:

```bash
cp .env.example .env
```

Edit `.env`:

```
GROQ_API_KEY=gsk_your_real_key_here
```

> 💡 You don't *have* to use a `.env` file — the app also lets you paste your API
> key directly into the sidebar at runtime. The environment variable is just a
> convenient default so you don't have to re-enter it every time.

### 5. Run the app

```bash
python app.py
```

Gradio will start a local server (default: `http://localhost:7860`). Open that
URL in your browser.

---

## ⬆️ Uploading to GitHub

```bash
git init
git add .
git commit -m "Initial commit: CodeMentor AI"
git branch -M main
git remote add origin https://github.com/<your-username>/codementor-ai.git
git push -u origin main
```

> ⚠️ **Important:** `.env` should never be committed. If you initialized git
> before creating `.env`, add a `.gitignore` file first:
>
> ```bash
> echo ".env" >> .gitignore
> echo "venv/" >> .gitignore
> echo "__pycache__/" >> .gitignore
> ```

---

## ☁️ Deploying to Hugging Face Spaces

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space).
   - **SDK**: choose **Gradio**
   - **Hardware**: the free CPU tier is sufficient (Groq does the heavy lifting remotely)
2. Push your code to the Space's git repo (Spaces work just like a normal git remote):
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/codementor-ai
   git push space main
   ```
   Or upload the files (`app.py`, `requirements.txt`, `README.md`) directly through
   the Spaces web UI.
3. Set your secret API key in the Space:
   - Go to your Space → **Settings** → **Variables and secrets**
   - Add a new secret: `GROQ_API_KEY` = `gsk_your_real_key_here`
4. The Space will automatically install `requirements.txt` and launch `app.py`.
   Because the code falls back to `os.environ.get("GROQ_API_KEY")`, no code
   changes are needed — it will just work once the secret is set.

> Spaces automatically restart on push and expose the Gradio app publicly at
> `https://huggingface.co/spaces/<your-username>/codementor-ai`.

---

## ☁️ Deploying to Streamlit Cloud (via Gradio embed) or alternative platforms

CodeMentor AI's UI is built with **Gradio**, not Streamlit, so there is no native
`streamlit run` entry point. You have two good options if you specifically want
Streamlit Cloud or a similar PaaS:

### Option A — Deploy as-is on a generic Python host (Render, Railway, Fly.io, etc.)
Most of these platforms just need a start command and the `PORT` environment
variable, which `app.py` already reads:

```bash
python app.py
```

Set the following environment variables in the platform's dashboard:
- `GROQ_API_KEY`
- `PORT` (many platforms set this automatically)

### Option B — Wrap the Gradio app for Streamlit Cloud
If you must deploy specifically to Streamlit Cloud, create a thin wrapper
(`streamlit_app.py`) that launches the Gradio app in a background thread and
embeds it via an iframe, or — more simply — port the six tab functions
(`explain_code`, `detect_bugs`, `generate_hints`, `translate_code`,
`generate_tests`, `analyze_complexity` in `app.py`) into native Streamlit
widgets (`st.text_area`, `st.selectbox`, `st.button`). The Groq backend logic
in `app.py` is UI-framework-agnostic and can be imported directly:

```python
# streamlit_app.py (example skeleton)
import streamlit as st
from app import explain_code, AVAILABLE_MODELS, SUPPORTED_LANGUAGES

st.title("🤖 CodeMentor AI")
api_key = st.text_input("Groq API Key", type="password")
model = st.selectbox("Model", AVAILABLE_MODELS)
language = st.selectbox("Language", SUPPORTED_LANGUAGES)
code = st.text_area("Code or Problem Description", height=300)

if st.button("Explain"):
    st.markdown(explain_code(api_key, model, language, code, "Intermediate (balanced)"))
```

Because all Groq/LLM logic lives in plain Python functions in `app.py`
(decoupled from Gradio components in `build_app()`), reusing it from Streamlit
requires no backend changes.

---

## 🔑 API Key Handling

The app resolves your Groq API key in this order:

1. **Sidebar input** — pasted directly into the running app (session-only, never persisted).
2. **`GROQ_API_KEY` environment variable** — loaded automatically via `python-dotenv`
   from a local `.env` file, or injected by your hosting platform's secrets manager.

If neither is present, each tab will show a clear inline warning instead of
crashing. Use the **"🔌 Test Connection"** button in the sidebar to verify your
key and chosen model work before using the tabs.

---

## 🧯 Error Handling

`app.py` gracefully handles and clearly reports:

- ❌ Missing / empty API key
- 🔑 Invalid API key (authentication errors)
- 🚦 Rate limiting
- ⏱️ Request timeouts (60s default, configurable via `REQUEST_TIMEOUT_SECONDS` in `app.py`)
- 🌐 Network/connection failures
- ❌ Unexpected Groq API status errors

All errors are surfaced inline in the relevant tab's output box — the app never
crashes on a bad request.

---

## 🛠️ Customization

- **Change the default model**: edit `DEFAULT_MODEL` in `app.py`.
- **Add/remove models**: edit the `AVAILABLE_MODELS` list.
- **Add a language**: add it to `SUPPORTED_LANGUAGES` (and `TEST_FRAMEWORKS` if it
  needs a specific test framework list).
- **Tune creativity**: each feature function calls `call_groq(...)` with its own
  `temperature` — lower for deterministic tasks (bug detection, translation),
  higher for more exploratory tasks (hints).

---

## 📜 License

This project is provided as-is for educational purposes. Add your preferred
license (MIT, Apache 2.0, etc.) here before publishing.
