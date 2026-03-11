# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AAAI (Another AI Assistant for Interview) — a Python tool that captures screenshots via global keyboard hotkeys, analyzes them with LLMs, and presents results through a web dashboard and email notifications.

## Running the Application

```bash
# Install dependencies (uv preferred)
uv sync

# Or with pip
pip install -r requirements.txt

# Run
uv run python main.py
# or: python main.py
```

The app requires a `config.json` file (copy from `config_example.json`). This file contains API keys and is gitignored.

## Building

```bash
# Package as standalone Windows exe via PyInstaller
python build.py
```

## Architecture

Single-process, multi-threaded Python application orchestrated by `ScreenCaptureApp` in `main.py`.

**Event flow:** Keyboard listener detects 3 rapid Enter presses → `screenshot.py` captures screen → `llm_manager.py` analyzes image → result posted to web server API + optional email notification.

**Key modules:**
- `main.py` — Entry point, `ScreenCaptureApp` wires all components, manages lifecycle and signal handling
- `keyboard_listener.py` — Global keyboard monitoring via pynput, daemon thread, callback-based trigger
- `screenshot.py` — PIL-based screen capture, auto-cleanup (keeps 10 latest)
- `llm_manager.py` — Multi-provider LLM abstraction (Ollama, OpenAI, Claude, Doubao, Qianwen). Handles text and vision models with base64 image encoding
- `email_sender.py` — SMTP email with screenshot attachments and LLM analysis
- `web_server.py` — FastAPI REST API + Jinja2 frontend. Data persisted in `web_data/results.json`

**Frontend:** SPA in `templates/index.html` + `static/` with 5-second auto-refresh, markdown rendering.

## Configuration

All behavior driven by `config.json` with sections: `email`, `web_service`, `screenshot`, `hotkeys`, `llm`.

LLM config uses two levels: `llm.vision_model` / `llm.text_model` select active provider+model, while `llm.<provider>` holds provider-specific settings (API keys, base URLs, timeouts).

**Provider-specific timeout settings:**
- `ollama.timeout` — HTTP request timeout for Ollama API (default: 60s)
- `openai.timeout` — SDK client timeout for OpenAI API (default: 60s)
- `claude.timeout` — SDK client timeout for Claude API (default: 60s)
- `doubao.timeout` — HTTP request timeout for Doubao API (default: 60s)
- `qianwen.timeout` — HTTP request timeout for Qianwen API (default: 60s)

All timeout values are in seconds. Custom API providers inherit timeout from their provider config.

**Provider-specific max_tokens settings:**
- `openai.max_tokens` — (Optional) Maximum tokens in response for OpenAI API. If not specified, OpenAI will use a reasonable default based on the model.
- `claude.max_tokens` — (Required) Maximum tokens in response for Claude API (default: 8192)

Note: Ollama, Doubao, and Qianwen do not use max_tokens configuration.

## Conventions

- Python 3.13+, dependencies managed via uv (pyproject.toml) or pip (requirements.txt)
- All modules use Python `logging` — colored console + file logging under `logs/`
- Chinese language in UI, logs, comments, and docs
- Runtime data: `web_data/` (images + results.json), local screenshots in `screenshots/`
- No test suite currently