# Equalize NYC — Codebase Reference

Multimodal civic advocate app for NYC small businesses fighting municipal fines.
Stack: Streamlit + Vertex AI (Google GenAI SDK 2026 syntax).

---

## Architecture Overview

```
.env / credentials.json
        │
        ▼
    config.py          ← single source of truth for all env vars
        │
   ┌────┴────┐
   ▼         ▼
ai_engine.py  live_engine.py   ← two AI backends (batch vs. live)
   │              │
   └──────┬───────┘
          ▼
       app.py              ← Streamlit UI (two tabs)
          │
   data_manager.py         ← loads nyc_rules.txt as context

Standalone scripts:
  chat_live.py             ← terminal voice chat (mic → AI → speakers)
  test_live.py             ← API smoke test (text → audio, no mic needed)
  test_auth.py             ← minimal auth/connectivity check
```

---

## File Reference

### `config.py`
**Purpose:** Loads and validates all environment variables. Every other module imports from here instead of reading env vars directly.

**Exports:**
| Name | Type | Default | Description |
|---|---|---|---|
| `PROJECT_ID` | `str` | `""` | GCP project ID (`GCP_PROJECT_ID`) |
| `LOCATION` | `str` | `"global"` | Vertex AI region for standard generate calls (`GCP_LOCATION`) |
| `LIVE_LOCATION` | `str` | `"us-central1"` | Region for Live API websocket — must be regional, not `"global"` (`GCP_LIVE_LOCATION`) |
| `CREDENTIALS_PATH` | `str` | `"credentials.json"` | Path to service account JSON (`GOOGLE_APPLICATION_CREDENTIALS`) |

**Functions:**
- `validate() -> None` — checks all three vars are set and the credentials file exists. Raises `ValueError` with per-field fix hints if anything is missing. Called at construction time by both engine classes.

**Notes:** Automatically loads `.env` via `python-dotenv` if installed (silent no-op if not).

---

### `ai_engine.py`
**Purpose:** Batch (non-streaming) multimodal analysis. Sends an image, optional voice transcript text, and optional compliance context to Gemini in a single request and returns a text response.

**Class: `CivicAI`**

```python
ai = CivicAI()
result: str = ai.analyze_incident(image_bytes, voice_text, context_text)
```

| Method | Signature | Description |
|---|---|---|
| `__init__` | `()` | Calls `config.validate()`, sets up `genai.Client` with `vertexai=True`, `location=global` |
| `analyze_incident` | `(image_bytes: bytes\|None, voice_text: str\|None, context_text: str\|None) -> str` | Builds a multimodal prompt and returns the AI's text recommendation |

**Model:** `gemini-3-flash-preview`
**Persona:** Predatory fine advocate — aggressive, cites exact rules, assumes every fine is challengeable.
**Used by:** `app.py` (Check Compliance tab)

---

### `live_engine.py`
**Purpose:** Real-time bidirectional audio session via Gemini's BidiGenerateContent WebSocket (`client.aio.live.connect`). Supports streaming mic audio in, streaming PCM audio out, mid-session image injection, and text turns.

**Module-level constants:**
- `SYSTEM_PROMPT` — same predatory fine advocate persona; adds a language-matching directive (always respond in the user's language)
- `LIVE_CONFIG` — `types.LiveConnectConfig` with `response_modalities=["AUDIO"]` and `output_audio_transcription` enabled

**Class: `CivicAILive`**

```python
# As async context manager (recommended)
async with CivicAILive() as ai:
    await ai.send_audio(pcm_bytes)
    async for chunk in ai.receive_turn():
        ...

# Manual lifecycle
ai = CivicAILive()
await ai.start_session()
await ai.send_text("question")
await ai.close()
```

| Method | Signature | Description |
|---|---|---|
| `start_session` | `async () -> None` | Opens the BidiGenerateContent WebSocket. Stores context manager in `self._cm` and session in `self._session` |
| `send_text` | `async (text: str) -> None` | Sends a text turn with `turn_complete=True` — triggers an immediate AI response |
| `send_audio` | `async (audio_bytes: bytes) -> None` | Streams a raw PCM chunk. Format: `audio/pcm;rate=16000`, 16-bit mono. VAD is server-side |
| `send_image` | `async (image_bytes: bytes) -> None` | Injects a JPEG frame mid-session via `LiveClientRealtimeInput` |
| `receive_turn` | `async () -> AsyncIterator[str\|bytes]` | Yields chunks until `turn_complete`. Yields `bytes` (PCM audio) or `str` (transcription). Catches `APIError(1000)` silently |
| `receive` | `async () -> AsyncIterator[str\|bytes]` | Same as `receive_turn` but never breaks — runs until connection closes. Use for persistent sessions |
| `close` | `async () -> None` | Calls `__aexit__` on the stored context manager. Safe to call if session was never opened |

**Model:** `gemini-live-2.5-flash-native-audio`
**Location:** `config.LIVE_LOCATION` (`us-central1` by default — `"global"` is not supported for Live API)
**Audio output:** 24 kHz LINEAR16 mono PCM
**Audio input:** 16 kHz LINEAR16 mono PCM (`audio/pcm;rate=16000`)
**Used by:** `app.py` (Live Session tab), `chat_live.py`, `test_live.py`

---

### `data_manager.py`
**Purpose:** Loads `nyc_rules.txt` from the project root as a compliance context block to inject into AI prompts.

**Functions:**

| Function | Signature | Description |
|---|---|---|
| `load_rules` | `() -> str` | Reads `nyc_rules.txt`. Returns `""` if file doesn't exist |
| `load_nyc_rules` | `() -> str` | Canonical alias for `load_rules()` |
| `chunk_text` | `(text: str, chunk_size: int = 800_000) -> list[str]` | Splits text into chunks only if it exceeds `chunk_size` chars. Gemini supports ~1M tokens so this is a safety fallback |
| `get_context_block` | `() -> str` | Returns the full rules as one string (or first chunk if enormous). This is the function to call from AI engines |

**Used by:** `app.py` (Check Compliance tab injects context into `CivicAI.analyze_incident`)

---

### `app.py`
**Purpose:** Streamlit UI. Two tabs — batch compliance check and live voice session.

**Tab 1 — Check Compliance:**
- Left column: `st.camera_input` for photo of violation
- Right column: `st.audio_input` for spoken question
- Button triggers `CivicAI().analyze_incident()`
- Output: `st.expander` with raw rules, `st.success` with AI recommendation

**Tab 2 — Live Session:**
- Start/Stop buttons manage a `CivicAILive` session running in a background daemon thread with its own asyncio event loop
- `st.audio_input` → enqueued as `{"type": "audio", ...}` → `live_engine.send_audio()`
- `st.camera_input` → enqueued as `{"type": "image", ...}` → `live_engine.send_image()`
- `st.empty()` display refreshes every 500ms via `time.sleep(0.5) + st.rerun()`
- Thread-safe handoff via two `queue.Queue` instances (`live_input_q`, `live_output_q`)

**Key session_state keys:**

| Key | Type | Description |
|---|---|---|
| `live_running` | `bool` | Whether a live session is active |
| `live_input_q` | `queue.Queue` | Mic/image bytes going into the live engine |
| `live_output_q` | `queue.Queue` | Text chunks coming out of the live engine |
| `live_stop_event` | `threading.Event` | Set to signal the background thread to exit |
| `live_response` | `str` | Accumulated AI response text for display |

**Run with:** `python -m streamlit run app.py`

---

### `chat_live.py`
**Purpose:** Standalone terminal voice chat. Mic → Live API → speakers, with barge-in support and auto-reconnect. No Streamlit dependency.

**Audio pipeline:**
```
sounddevice InputStream (16 kHz) → asyncio mic_q → send_loop → CivicAILive.send_audio()
                                                                        │
sounddevice RawOutputStream (24 kHz) ← speaker thread ← speaker_q ← receive_loop
```

**Key design decisions:**
- Mic callback uses `loop.call_soon_threadsafe(mic_q.put_nowait, data)` to safely cross the thread boundary into the asyncio event loop
- `receive_loop` never breaks on `turn_complete` — session stays open for multi-turn conversation; the model's VAD handles barge-in naturally
- On server-side close (`APIError(1000)`), the outer `while` loop reconnects with a 1s delay
- Speaker playback runs in its own thread draining a regular `queue.Queue` (thread-safe, no asyncio needed)

**Functions:**
- `mic_check(seconds=4)` — shows live level meter before connecting; exits with code 1 if no signal detected
- `run()` — async main: opens mic, loops session connect/send/receive, handles shutdown

**Run with:** `python chat_live.py`
**Requires:** `pip install sounddevice numpy`

---

### `test_live.py`
**Purpose:** Standalone debug script. Validates config, opens a `CivicAILive` session, sends one hardcoded text question, streams the audio response, and prints timing. No mic or speakers required.

**Output format:**
```
── Config Check ──────────────────────────────────────────
  ✔ GCP_PROJECT_ID  (your-project)
  ✔ GCP_LOCATION  (global)
  ✔ GOOGLE_APPLICATION_CREDENTIALS  (credentials.json)

── Opening Live Session ──────────────────────────────────
  Session opened  (1.11s)

── Streaming response ────────────────────────────────────
  [first audio chunk in 0.70s]
  audio chunk: 11,114 bytes  (total 11,114)
  ...

── Summary ───────────────────────────────────────────────
  Audio received  : 1,126,634 bytes
  Total time      : 7.50s
```

**Run with:** `python test_live.py`

---

### `test_auth.py`
**Purpose:** Minimal one-shot connectivity check. Sends `"Ping!"` to `gemini-3-flash-preview` via Vertex AI and prints success or the raw error. Use this first when debugging auth issues.

**Run with:** `python test_auth.py`

---

## Environment Variables

Defined in `.env` (copy from `.env.example`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `GCP_PROJECT_ID` | Yes | — | Your GCP project ID |
| `GCP_LOCATION` | No | `global` | Vertex AI region for batch Gemini calls |
| `GCP_LIVE_LOCATION` | No | `us-central1` | Region for Live API WebSocket (must be regional) |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | `credentials.json` | Path to service account key file |

---

## Data Files

| File | Description |
|---|---|
| `credentials.json` | GCP service account key. Gitignored. Required for auth |
| `nyc_rules.txt` | NYC compliance rules injected as context into batch AI calls. Optional — app works without it but responses will lack specific rule citations |
| `.env` | Local environment config. Gitignored. Copy from `.env.example` |
| `.env.example` | Template listing all required env vars with placeholder values |
