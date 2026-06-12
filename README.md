# KAREN — Desktop AI Companion

> **Honest framing upfront:** I designed the system architecture and feature set, researched and specified every component, and debugged real integration issues (GPU drivers, threading crashes, audio pipelines). The implementation code was written with AI assistance. I'm sharing this because I want to understand the codebase well enough to maintain and extend it myself — that's the point of showing it to you.

---

## What is KAREN?

KAREN is a local, privacy-first AI desktop companion that runs entirely on your own machine. No cloud, no subscriptions, no data leaving your system. It sits in your taskbar as an animated orb, listens for your voice, reads your screen context, and talks back — like J.A.R.V.I.S. but actually yours.

---

## What I actually built

This wasn't a "download a template and run it" project. Here's what required real design decisions:

**Systems design:**
- Chose Whisper over cloud STT specifically because it runs offline and handles accented English well
- Picked ChromaDB as the memory backend because it supports semantic similarity search — so KAREN recalls relevant past conversations even when phrased differently
- Designed a vision pipeline where passive screenshots are summarized by LLaVA and injected as context — KAREN knows what you're looking at without you describing it
- Threaded every I/O operation (LLM calls, TTS, STT, vision) off the main Qt thread — learned the hard way what a frozen UI looks like

**Real debugging I did:**
- PyAudio vs PortAudio driver conflicts on Windows — had to match CUDA toolkit versions with the PyTorch build Whisper expects
- Qt signal/slot threading model crashes when workers emit signals after the thread has already quit — fixed with proper cleanup order
- Piper TTS writes to a temp WAV file and `playsound` can't handle paths with spaces on Windows — workaround: `tempfile.NamedTemporaryFile` with a fixed suffix
- ChromaDB distance threshold tuning — set too low stores duplicate topics, too high misses near-duplicates

**Where the gap is:**
I understand *what* each module does and *why* it's designed this way. I don't yet have deep fluency in the PyQt6 event loop internals or the threading primitives. That's what I want to close.

---

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| LLM | Ollama + Gemma 2 9B | Local, fast, good instruction following |
| Vision | Ollama + LLaVA 7B | Multimodal, same Ollama server |
| STT | OpenAI Whisper (base) | Offline, handles accents, fast enough |
| TTS | Piper TTS | Low latency, natural voice, fully local |
| Memory | ChromaDB | Persistent vector store, semantic retrieval |
| GUI | PyQt6 | Native widgets, proper threading model |
| Screen capture | mss | Fast multi-monitor screenshot |

---

## Project Structure

```
karen-ai/
├── main.py                  ← Entry point (5 lines)
├── requirements.txt
├── config/
│   └── settings.py          ← Every constant, path, prompt, and app registry
├── core/
│   ├── memory.py            ← ChromaDB: conversations, patterns, topics
│   ├── vision.py            ← Screenshot capture + LLaVA summarizer
│   └── speech.py            ← Whisper STT, Piper TTS, wake word listener
└── gui/
    ├── orb.py               ← Animated orb + particle system (pure PyQt6)
    └── window.py            ← Main widget, tray app, all QThread wiring
```

The import chain is strictly one-way: `gui → core → config`. Nothing in `core/` imports from `gui/`. The AI logic can be tested independently of the interface.

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Ollama and pull models

```bash
# Install from https://ollama.com
ollama pull gemma2:9b
ollama pull llava:7b
```

### 3. Install Piper TTS

Download from [rhasspy/piper](https://github.com/rhasspy/piper/releases). Then update these two lines in `config/settings.py`:

```python
PIPER_EXE   = r"C:\piper\piper\piper.exe"
PIPER_MODEL = r"C:\piper\en_US-lessac-high.onnx"
```

### 4. Run

```bash
python main.py
```

KAREN appears as an orb in the bottom-right corner. Say **"Karen"** to activate the mic, or just type in the chat box.

---

## Configuration

Everything you'd want to change is in `config/settings.py`:

```python
USER_NAME     = "Arvindh"    # How KAREN addresses you
MODEL         = "gemma2:9b"  # Swap to llama3 or mistral if you want
WHISPER_MODEL = "base"       # "small" = more accurate, "tiny" = faster
WAKE_WORD     = "karen"      # Change to anything
SCREENSHOT_RETAIN_HOURS = 12 # How long screen captures are kept
```

---

## Features

- **Voice input** — hold the mic button or say the wake word
- **Streaming responses** — tokens appear as they're generated, not all at once
- **Screen awareness** — passive screenshots every 5 min, summarized and used as context
- **Long-term memory** — ChromaDB stores summaries, patterns, and topics across sessions
- **App launcher** — say "open Chrome" or "launch VS Code", it finds and starts the executable
- **Weekly report** — generates an HTML report of activity, topics, and behavioural patterns
- **System tray** — lives in your taskbar, never in your way

---

## What I Want to Learn Next

- The PyQt6 `QThread` + `QObject` worker pattern — why `moveToThread` instead of subclassing `QThread`
- How ChromaDB's HNSW index actually does similarity search
- The Whisper architecture — why the "base" model handles noise better than expected
- How to replace Piper with streaming TTS so responses start speaking before the full text is ready

---

*All data stays local. Screenshots deleted after 12 hours. Memory lives in `~/.karen/`.*
