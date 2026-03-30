import streamlit as st
import queue
import asyncio
import threading
import base64 as _base64
import uuid as _uuid

# Must import backend modules
from live_engine import CivicAILive
from ai_engine import CivicAI
from data_manager import get_context_block
from components.high_res_camera import high_res_camera as _high_res_camera

# ── Audio constants (real-time mic/speaker via sounddevice) ───────────────────
MIC_RATE     = 16_000
SPEAKER_RATE = 24_000
CHANNELS     = 1
DTYPE        = "int16"
MIC_CHUNK    = 1_024

# ── Per-session registries (process-level store, keyed by browser session ID) ─
@st.cache_resource
def _all_registries() -> dict:
    """One shared dict that holds a registry per browser session."""
    return {}

def _registry() -> dict:
    """Return the registry for THIS browser session only, creating it if needed."""
    sid = st.session_state["_session_id"]
    store = _all_registries()
    if sid not in store:
        store[sid] = {
            "thread":        None,
            "stop_event":    None,
            "lock":          threading.Lock(),
            "photo_context": [""],  # fresh every new browser session
            "conv_history":  [""],  # fresh every new browser session
        }
    return store[sid]

# Configure page
st.set_page_config(
    page_title="Equalize NYC - Analyze",
    page_icon="⚖️",
    layout="centered",
)

# ─────────────────────────────────────────────────────────────────────────────
# DARK THEME CSS & MOBILE STYLING
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        background-color: #0e0e0e;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
    }
    
    .main {
        background-color: #0e0e0e;
    }
    
    .block-container {
        max-width: 400px !important;
        margin: 0 auto !important;
        padding: 1rem !important;
    }
    
    /* App Header */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.5rem 0;
        border-bottom: 1px solid #2a2a2a;
        margin-bottom: 1.5rem;
    }
    
    .header-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
    }
    
    .header-subtitle {
        font-size: 0.8rem;
        color: #a0a0a0;
        margin-top: 0.25rem;
    }
    
    /* Camera Button - Top Right */
    .camera-button-container {
        position: relative;
        margin-bottom: 2rem;
    }
    
    .camera-button {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: #4f46e5;
        border: none;
        color: #ffffff;
        font-size: 1.8rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
        margin: 0 auto !important;
    }
    
    .camera-button:hover {
        background-color: #4338ca;
        transform: scale(1.1);
        box-shadow: 0 6px 25px rgba(79, 70, 229, 0.4);
    }
    
    .camera-button:active {
        transform: scale(0.95);
    }
    
    /* Response Display Box */
    .response-box {
        background-color: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 2rem 0;
        min-height: 200px;
        max-height: 400px;
        overflow-y: auto;
        color: #e0e0e0;
        line-height: 1.6;
        font-size: 0.95rem;
    }
    
    .response-box::-webkit-scrollbar {
        width: 6px;
    }
    
    .response-box::-webkit-scrollbar-track {
        background: #0e0e0e;
    }
    
    .response-box::-webkit-scrollbar-thumb {
        background: #4f46e5;
        border-radius: 3px;
    }
    
    .response-box::-webkit-scrollbar-thumb:hover {
        background: #4338ca;
    }
    
    /* Response Label */
    .response-label {
        font-size: 0.9rem;
        color: #a0a0a0;
        margin-bottom: 1rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Image Preview */
    .image-preview {
        width: 100%;
        max-width: 350px;
        margin: 1rem auto;
        border-radius: 8px;
        border: 2px solid #2a2a2a;
        display: block;
    }
    
    /* Mute Button - Bottom */
    .mute-button-container {
        display: flex;
        justify-content: center;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    .mute-button {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        background-color: #4f46e5;
        border: none;
        color: #ffffff;
        font-size: 2rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
    }
    
    .mute-button:hover {
        background-color: #4338ca;
        transform: scale(1.1);
        box-shadow: 0 6px 25px rgba(79, 70, 229, 0.4);
    }
    
    .mute-button:active {
        transform: scale(0.95);
    }
    
    .mute-button.muted {
        background-color: #6b5b3e;
        box-shadow: 0 4px 15px rgba(107, 91, 62, 0.3);
    }
    
    .mute-button.muted:hover {
        background-color: #7a6b4a;
    }
    
    /* Status indicators */
    .status-badge {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    .status-recording {
        background-color: rgba(79, 70, 229, 0.2);
        color: #4f46e5;
    }
    
    .status-waiting {
        background-color: rgba(160, 160, 160, 0.1);
        color: #a0a0a0;
    }
    
    /* Divider */
    .divider {
        height: 1px;
        background: linear-gradient(to right, transparent, #4f46e5, transparent);
        margin: 2rem 0;
    }
    
    /* Language indicator */
    .language-pill {
        display: inline-block;
        background-color: #2a2a2a;
        color: #4f46e5;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    /* Subtitle display */
    .subtitle-display {
        text-align: center;
        padding: 0.75rem 1.25rem;
        background: rgba(0, 0, 0, 0.75);
        border-radius: 8px;
        color: #ffffff;
        font-size: 1.15rem;
        font-weight: 500;
        line-height: 1.5;
        min-height: 64px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0.5rem 0 1rem 0;
        letter-spacing: 0.01em;
    }

    .subtitle-placeholder {
        color: #555555;
        font-size: 0.95rem;
        font-weight: 400;
    }
    
    /* Delete button (back to start) */
    .back-button {
        text-align: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #2a2a2a;
    }
    
    .back-button button {
        background-color: #2a2a2a !important;
        color: #a0a0a0 !important;
        border: none !important;
        padding: 0.7rem 1.5rem !important;
        border-radius: 8px !important;
        font-size: 0.9rem !important;
    }
    
    .back-button button:hover {
        background-color: #3a3a3a !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

# Unique ID for this browser session — used to isolate registry data per tab
if "_session_id" not in st.session_state:
    st.session_state["_session_id"] = str(_uuid.uuid4())

if "captured_image" not in st.session_state:
    st.session_state.captured_image = None
    
if "muted" not in st.session_state:
    st.session_state.muted = False
    
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
    
if "selected_language" not in st.session_state:
    st.session_state.selected_language = "en"

if "live_running" not in st.session_state:
    st.session_state.live_running = False

# ─────────────────────────────────────────────────────────────────────────────
# LIVE SESSION HELPERS  (real-time mic → API → speaker)
# ─────────────────────────────────────────────────────────────────────────────

async def _live_main(
    image_q: queue.Queue,
    output_q: queue.Queue,
    stop_event: threading.Event,
    mute_event: threading.Event,
    speaker_q: queue.Queue,
    photo_context: list,          # photo_context[0] = latest analysis text
    conv_history: list,           # conv_history[0] = rolling transcript for context continuity
) -> None:
    """Opens mic stream, connects to Live API, reconnects on drop."""
    import sounddevice as sd
    import time as _time

    loop = asyncio.get_running_loop()
    mic_async_q: asyncio.Queue = asyncio.Queue()

    def _mic_callback(indata, frames, time_info, status) -> None:
        if not stop_event.is_set():
            loop.call_soon_threadsafe(mic_async_q.put_nowait, indata.tobytes())

    # Outer loop: restarts the mic stream if sounddevice fails
    while not stop_event.is_set():
      try:
        output_q.put("[Mic open — connecting...]")
        with sd.InputStream(
            samplerate=MIC_RATE, channels=CHANNELS, dtype=DTYPE,
            blocksize=MIC_CHUNK, callback=_mic_callback,
        ):
          _reconnect_delay = [0.7]  # exponential backoff state; reset on clean connect
          while not stop_event.is_set():
            try:
                async with CivicAILive(
                    photo_context=photo_context[0],
                    conv_history=conv_history[0],
                ) as engine:
                    output_q.put("[Connected — speak now]")
                    _reconnect_delay[0] = 0.7  # reset backoff on successful connection

                    ai_speaking = asyncio.Event()
                    _last_audio: list[float] = [0.0]
                    _photo_ready = asyncio.Event()

                    # Shared drain helper — used by both _send and _recv
                    def _drain_mic():
                        while True:
                            try:
                                mic_async_q.get_nowait()
                            except asyncio.QueueEmpty:
                                break

                    async def _send() -> None:
                        _loop = asyncio.get_running_loop()

                        while not stop_event.is_set():
                            # Fallback echo suppression: if turn_complete sentinel was missed
                            # and 8s have passed since last audio chunk, clear ai_speaking.
                            if ai_speaking.is_set() and _time.monotonic() - _last_audio[0] > 8.0:
                                ai_speaking.clear()
                                _drain_mic()

                            # Reconnect once background photo analysis finishes.
                            if _photo_ready.is_set():
                                raise Exception("photo_updated")

                            try:
                                item = image_q.get_nowait()
                                output_q.put("[Analyzing photo...]")
                                # Run analysis in background so audio keeps flowing.
                                captured_item = item
                                async def _bg_analyze():
                                    def _analyze():
                                        ai = CivicAI()
                                        ctx = get_context_block()
                                        return ai.analyze_incident(
                                            image_bytes=captured_item["data"],
                                            voice_text="Analyze this violation notice and give every argument to fight it.",
                                            context_text=ctx if ctx else None,
                                        )
                                    try:
                                        result = await _loop.run_in_executor(None, _analyze)
                                        photo_context[0] = result
                                        _photo_ready.set()
                                    except Exception as e:
                                        output_q.put(f"[Photo analysis failed: {e}]")
                                asyncio.create_task(_bg_analyze())
                            except queue.Empty:
                                pass

                            # While AI is speaking: drain mic only — sending silence keepalives
                            # was triggering native-audio VAD and causing barge-in cutoffs.
                            if ai_speaking.is_set():
                                _drain_mic()
                                await asyncio.sleep(0.05)
                                continue

                            try:
                                chunk = await asyncio.wait_for(
                                    mic_async_q.get(), timeout=0.1
                                )
                                # Re-check after await — _recv() may have set ai_speaking
                                # during the wait, making this chunk a barge-in trigger.
                                if not ai_speaking.is_set():
                                    await engine.send_audio(chunk)
                            except asyncio.TimeoutError:
                                pass

                    async def _recv() -> None:
                        async for chunk in engine.receive():
                            if stop_event.is_set():
                                return
                            if chunk is None:
                                # turn_complete: wait for speaker_q to empty, then add a
                                # hardware-buffer grace period before re-opening the mic.
                                # Fixed delays are unreliable — long responses need more time.
                                async def _wait_speaker_drain():
                                    deadline = _time.monotonic() + 8.0
                                    while not speaker_q.empty() and _time.monotonic() < deadline:
                                        await asyncio.sleep(0.05)
                                    await asyncio.sleep(0.5)  # sounddevice hardware buffer
                                    ai_speaking.clear()
                                asyncio.create_task(_wait_speaker_drain())
                            elif isinstance(chunk, bytes):
                                ai_speaking.set()
                                _last_audio[0] = _time.monotonic()
                                speaker_q.put(chunk)
                            elif isinstance(chunk, str) and chunk:
                                output_q.put(chunk)
                                combined = (conv_history[0] + f"\nAssistant: {chunk}").strip()
                                conv_history[0] = combined[-8000:]

                    send_t = asyncio.create_task(_send())
                    recv_t = asyncio.create_task(_recv())
                    done, pending = await asyncio.wait(
                        {send_t, recv_t},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for t in pending:
                        t.cancel()
                    await asyncio.gather(*pending, *done, return_exceptions=True)
                    # Re-raise any exception (e.g. photo_updated, APIError) so the
                    # outer handler can log it and trigger a proper reconnect.
                    for t in done:
                        if not t.cancelled() and t.exception() is not None:
                            raise t.exception()

            except Exception as exc:
                if not stop_event.is_set():
                    is_photo = "photo_updated" in str(exc)
                    msg = "[Photo ready — reconnecting...]" if is_photo else f"[Reconnecting: {exc}]"
                    output_q.put(msg)
                    if not is_photo:
                        # Advance backoff on real errors (e.g. 1011 resource exhausted)
                        _reconnect_delay[0] = min(_reconnect_delay[0] * 2, 30.0)

            finally:
                if not stop_event.is_set():
                    # Wait for in-flight audio to finish playing before reconnecting.
                    _drain_start = _time.monotonic()
                    while not speaker_q.empty() and _time.monotonic() - _drain_start < 5.0:
                        await asyncio.sleep(0.1)
                # Force-drain residual chunks to prevent two-voice overlap.
                while True:
                    try:
                        speaker_q.get_nowait()
                    except queue.Empty:
                        break
                if not stop_event.is_set():
                    await asyncio.sleep(_reconnect_delay[0])
      except Exception as exc:
        if not stop_event.is_set():
            output_q.put(f"[Mic error, retrying: {exc}]")
            while True:
                try:
                    speaker_q.get_nowait()
                except queue.Empty:
                    break
            await asyncio.sleep(2)


def _run_live_thread(
    image_q: queue.Queue,
    output_q: queue.Queue,
    stop_event: threading.Event,
    mute_event: threading.Event,
    photo_context: list,
    conv_history: list,
) -> None:
    """Owns its own event loop, mic stream, and speaker stream."""
    try:
        import sounddevice as sd
        import numpy as np  # noqa: F401
    except ImportError:
        output_q.put("[sounddevice not installed — run: pip install sounddevice numpy]")
        return

    speaker_q: queue.Queue = queue.Queue()

    def _speaker_worker() -> None:
        try:
            with sd.RawOutputStream(
                samplerate=SPEAKER_RATE, channels=CHANNELS, dtype=DTYPE
            ) as stream:
                while not stop_event.is_set():
                    try:
                        chunk = speaker_q.get(timeout=0.5)
                        if chunk is None:
                            break
                        if not mute_event.is_set():
                            stream.write(chunk)
                    except queue.Empty:
                        pass
        except Exception as spk_exc:
            output_q.put(f"[Speaker error: {spk_exc}]")

    spk_thread = threading.Thread(target=_speaker_worker, daemon=True)
    spk_thread.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            _live_main(image_q, output_q, stop_event, mute_event, speaker_q, photo_context, conv_history)
        )
    except Exception as exc:
        output_q.put(f"[Fatal: {exc}]")
    finally:
        stop_event.set()
        speaker_q.put(None)
        spk_thread.join(timeout=2)
        loop.close()


def _start_live_session() -> None:
    reg = _registry()
    with reg["lock"]:
        # Re-check inside lock — concurrent reruns converge here
        if reg["thread"] and reg["thread"].is_alive():
            return

        # Stop any lingering thread
        if reg["stop_event"]:
            reg["stop_event"].set()

        # Re-use existing lists so analysis and history survive restarts
        photo_context: list = reg["photo_context"]
        conv_history: list  = reg["conv_history"]

        image_q: queue.Queue  = queue.Queue()
        output_q: queue.Queue = queue.Queue()
        stop_event  = threading.Event()
        mute_event  = threading.Event()
        thread = threading.Thread(
            target=_run_live_thread,
            args=(image_q, output_q, stop_event, mute_event, photo_context, conv_history),
            daemon=True,
        )
        thread.start()

        reg["thread"]     = thread
        reg["stop_event"] = stop_event

        st.session_state.live_running       = True
        st.session_state.live_input_q       = image_q
        st.session_state.live_output_q      = output_q
        st.session_state.live_stop_event    = stop_event
        st.session_state.live_mute_event    = mute_event
        st.session_state.live_thread        = thread
        st.session_state.transcript         = ""
        st.session_state.live_last_frame_id = None


def _stop_live_session() -> None:
    reg = _registry()
    thread = reg.get("thread")
    if reg.get("stop_event"):
        reg["stop_event"].set()
    # Wait up to 3 s for the thread to finish so the session is fully closed
    # before we return — prevents zombie sessions overlapping with new ones.
    if thread and thread.is_alive():
        thread.join(timeout=3)
    reg["thread"]     = None
    reg["stop_event"] = None
    st.session_state.live_running = False
    for key in (
        "live_input_q", "live_output_q", "live_stop_event",
        "live_mute_event", "live_thread", "live_last_frame_id",
    ):
        st.session_state.pop(key, None)


_SHOW_PREFIXES = ("[Reconnecting", "[Fatal", "[Photo", "[Speaker error", "[Analyzing")

def _drain_output_queue() -> str:
    """Pull AI transcription + notable status messages; skip routine connect/mic lines."""
    output_q: queue.Queue = st.session_state.live_output_q
    new_text = ""
    while True:
        try:
            chunk = output_q.get_nowait()
            if not isinstance(chunk, str):
                continue
            # Keep: regular AI text (no "[") or important status messages
            if not chunk.startswith("[") or any(chunk.startswith(p) for p in _SHOW_PREFIXES):
                new_text += chunk
        except queue.Empty:
            break
    return new_text

# ── AUTO-START: open live session the moment this page loads ──────────────────
_reg = _registry()
if _reg["thread"] is None or not _reg["thread"].is_alive():
    _start_live_session()

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE MAPPING
# ─────────────────────────────────────────────────────────────────────────────

LANGUAGE_MAP = {
    "en": "English",
    "es": "Español",
    "ru": "Русский",
    "yue": "粵語",
    "pt-br": "Português (Brasil)",
    "zh": "中文",
    "yi": "ייִדיש",
    "bn": "বাংলা",
    "it": "Italiano",
    "fr": "Français",
    "ht": "Kreyòl Ayisyen",
}

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="app-header">
    <div>
        <div class="header-title">⚖️ Equalize</div>
        <div class="header-subtitle">Document Analyzer</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Language indicator
lang_name = LANGUAGE_MAP.get(st.session_state.selected_language, "English")
st.markdown(f'<span class="language-pill">🌐 {lang_name}</span>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HIGH-RES CAMERA CAPTURE
# ─────────────────────────────────────────────────────────────────────────────

captured_data_url = _high_res_camera(key="hrc", default=None)

if captured_data_url is not None:
    import hashlib
    # Strip the data URL header and decode base64 → raw JPEG bytes
    header, b64 = captured_data_url.split(",", 1)
    img_bytes = _base64.b64decode(b64)
    img_hash = hashlib.md5(img_bytes).hexdigest()
    if img_hash != st.session_state.get("live_last_frame_id"):
        st.session_state.live_last_frame_id = img_hash
        st.session_state.captured_image = img_bytes
        if st.session_state.live_running:
            st.session_state.live_input_q.put(
                {"type": "image", "data": img_bytes}
            )

# ─────────────────────────────────────────────────────────────────────────────
# TRANSCRIPT STREAMING SECTION
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="response-label">Live Transcript</div>', unsafe_allow_html=True)

@st.fragment(run_every=0.5)
def _transcript_fragment():
    # Auto-restart if the background thread died (catches crashes between page reloads)
    reg = _registry()
    if st.session_state.live_running and (
        reg["thread"] is None or not reg["thread"].is_alive()
    ):
        _start_live_session()

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.live_running:
            st.markdown('<span class="status-badge status-recording">● Listening</span>', unsafe_allow_html=True)
    with col2:
        if st.session_state.live_running:
            if st.button("⏹", key="stop_live", help="Stop session"):
                _stop_live_session()
                st.rerun()

    if st.session_state.live_running:
        new_text = _drain_output_queue()
        if new_text:
            combined = (st.session_state.get("transcript", "") + " " + new_text).strip()
            st.session_state.transcript = combined[-180:]

        if st.session_state.transcript:
            st.markdown(
                f'<div class="subtitle-display">{st.session_state.transcript}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="subtitle-display"><span class="subtitle-placeholder">Listening...</span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="subtitle-display"><span class="subtitle-placeholder">Session stopped.</span></div>',
            unsafe_allow_html=True,
        )

_transcript_fragment()

# ─────────────────────────────────────────────────────────────────────────────
# MUTE BUTTON
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="mute-button-container">', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    # Derive mute state from the live_mute_event when session is running
    mute_event = st.session_state.get("live_mute_event")
    is_muted = mute_event.is_set() if mute_event else st.session_state.muted
    mute_label = "🔇" if is_muted else "🔊"
    if st.button(mute_label, key="mute_toggle", help="Toggle audio output"):
        if mute_event:
            if mute_event.is_set():
                mute_event.clear()
            else:
                mute_event.set()
        st.session_state.muted = not is_muted
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# Mute status
is_muted = st.session_state.get("live_mute_event", None)
is_muted = is_muted.is_set() if is_muted else st.session_state.muted
status_text = "Audio Muted" if is_muted else "Audio Enabled"
status_class = "status-recording" if not is_muted else "status-waiting"
st.markdown(f'<div style="text-align: center;"><span class="status-badge {status_class}">{status_text}</span></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# RESET SECTION
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="back-button">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("← Back", use_container_width=True, key="back_button"):
        st.session_state.captured_image = None
        st.session_state.transcript = ""
        if st.session_state.live_running:
            _stop_live_session()
        st.switch_page("app.py")
st.markdown('</div>', unsafe_allow_html=True)
