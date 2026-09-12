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
├── app.py              # Gradio UI + Groq backend logic (use for local/HF Spaces)
├── streamlit_app.py    # Streamlit UI, reuses app.py's Groq functions (use for Streamlit Cloud)
├── requirements.txt    # Python dependencies (covers both UIs)
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

## ☁️ Deploying to Streamlit Cloud

⚠️ **Important:** `app.py` is a Gradio app — it calls `gradio.launch()`, which
starts its **own** embedded web server on its own port. Streamlit Community
Cloud runs your script *inside its own* Streamlit server on a single,
platform-controlled port and does not allow a second server to bind a port
inside that container. If you point Streamlit Cloud's "Main file path" at
`app.py`, you'll hit:

```
OSError: Cannot find empty port in range: 7860-7860...
```

**Fix: point Streamlit Cloud at `streamlit_app.py` instead of `app.py`.**
This repo includes a native Streamlit UI (`streamlit_app.py`) that reuses
every Groq backend function from `app.py` (`explain_code`, `detect_bugs`,
`generate_hints`, `translate_code`, `generate_tests`, `analyze_complexity`,
`test_api_connection`) but renders them with real Streamlit widgets
(`st.tabs`, `st.text_area`, `st.selectbox`, `st.button`) instead of launching
a second server. No backend logic is duplicated or reimplemented.

### Steps
1. Push the whole repo (including `streamlit_app.py`) to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Point it at your repo, and set **Main file path** to:
   ```
   streamlit_app.py
   ```
   (NOT `app.py`)
4. Under **Advanced settings → Secrets**, add:
   ```toml
   GROQ_API_KEY = "gsk_your_real_key_here"
   ```
5. Deploy. `streamlit_app.py` automatically reads the key from
   `st.secrets["GROQ_API_KEY"]` (falling back to the sidebar input if you'd
   rather paste a key per-session).

### Running the Streamlit version locally
```bash
streamlit run streamlit_app.py
```

### Alternative: generic Python hosts (Render, Railway, Fly.io, etc.)
If you'd rather keep using the original Gradio `app.py` outside of Hugging
Face Spaces or Streamlit Cloud, most generic Python hosts are fine with it
since they don't pre-occupy a port the way Streamlit Cloud does:

```bash
python app.py
```

Set `GROQ_API_KEY` (and optionally `PORT`, which many platforms inject
automatically) in the platform's dashboard.

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
