import streamlit as st
import time
import queue
import asyncio
import threading

# Must import backend modules
from ai_engine import CivicAI
from live_engine import CivicAILive
from data_manager import get_context_block

# ── Audio constants (real-time mic/speaker via sounddevice) ───────────────────
MIC_RATE     = 16_000
SPEAKER_RATE = 24_000
CHANNELS     = 1
DTYPE        = "int16"
MIC_CHUNK    = 1_024

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
    
    /* Transcript streaming */
    .transcript-box {
        background-color: #161616;
        border-left: 3px solid #4f46e5;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        color: #c0c0c0;
        font-size: 0.9rem;
        line-height: 1.5;
        min-height: 60px;
    }
    
    .transcription-live {
        animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
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

if "captured_image" not in st.session_state:
    st.session_state.captured_image = None
    
if "muted" not in st.session_state:
    st.session_state.muted = False
    
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
    
if "ai_response" not in st.session_state:
    st.session_state.ai_response = ""
    
if "selected_language" not in st.session_state:
    st.session_state.selected_language = "en"

if "live_running" not in st.session_state:
    st.session_state.live_running = False

# ─────────────────────────────────────────────────────────────────────────────
# LIVE SESSION HELPERS  (real-time mic → API → speaker)
# ─────────────────────────────────────────────────────────────────────────────

async def _send_loop(
    engine: CivicAILive,
    mic_async_q: asyncio.Queue,
    image_q: queue.Queue,
    stop_event: threading.Event,
) -> None:
    """Stream mic audio continuously; also forward any camera image that arrives."""
    while not stop_event.is_set():
        # Drain any queued camera image first
        try:
            item = image_q.get_nowait()
            await engine.send_image(item["data"])
        except queue.Empty:
            pass
        # Send next mic chunk
        try:
            chunk = mic_async_q.get_nowait()
            if chunk is None:
                return
            await engine.send_audio(chunk)
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.02)


async def _receive_loop(
    engine: CivicAILive,
    output_q: queue.Queue,
    speaker_q: queue.Queue,
    stop_event: threading.Event,
) -> None:
    """Route audio chunks to the speaker queue; push transcription text to output_q."""
    async for chunk in engine.receive():
        if stop_event.is_set():
            break
        if isinstance(chunk, bytes):
            speaker_q.put(chunk)
        elif isinstance(chunk, str) and chunk:
            output_q.put(chunk)


async def _live_loop(
    engine: CivicAILive,
    mic_async_q: asyncio.Queue,
    image_q: queue.Queue,
    output_q: queue.Queue,
    speaker_q: queue.Queue,
    stop_event: threading.Event,
) -> None:
    async with engine:
        await asyncio.gather(
            _send_loop(engine, mic_async_q, image_q, stop_event),
            _receive_loop(engine, output_q, speaker_q, stop_event),
        )


def _run_live_thread(
    image_q: queue.Queue,
    output_q: queue.Queue,
    stop_event: threading.Event,
    mute_event: threading.Event,
) -> None:
    """Owns its own event loop, mic stream, and speaker stream."""
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        output_q.put("[sounddevice not installed — run: pip install sounddevice numpy]")
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    mic_async_q: asyncio.Queue = asyncio.Queue()
    speaker_q: queue.Queue = queue.Queue()

    def _mic_callback(indata: "np.ndarray", frames, time_info, status) -> None:
        if not stop_event.is_set():
            loop.call_soon_threadsafe(mic_async_q.put_nowait, indata.tobytes())

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
        except Exception:
            pass

    spk_thread = threading.Thread(target=_speaker_worker, daemon=True)
    spk_thread.start()

    engine = CivicAILive()
    try:
        with sd.InputStream(
            samplerate=MIC_RATE, channels=CHANNELS, dtype=DTYPE,
            blocksize=MIC_CHUNK, callback=_mic_callback,
        ):
            loop.run_until_complete(
                _live_loop(engine, mic_async_q, image_q, output_q, speaker_q, stop_event)
            )
    except Exception as exc:
        output_q.put(f"[session error: {exc}]")
    finally:
        stop_event.set()
        speaker_q.put(None)
        spk_thread.join(timeout=2)
        loop.close()


def _start_live_session() -> None:
    image_q: queue.Queue  = queue.Queue()   # camera frames → live engine
    output_q: queue.Queue = queue.Queue()   # transcription text → UI
    stop_event  = threading.Event()
    mute_event  = threading.Event()         # set = muted
    thread = threading.Thread(
        target=_run_live_thread,
        args=(image_q, output_q, stop_event, mute_event),
        daemon=True,
    )
    thread.start()
    st.session_state.live_running       = True
    st.session_state.live_input_q       = image_q
    st.session_state.live_output_q      = output_q
    st.session_state.live_stop_event    = stop_event
    st.session_state.live_mute_event    = mute_event
    st.session_state.live_thread        = thread
    st.session_state.transcript         = ""
    st.session_state.live_last_frame_id = None


def _stop_live_session() -> None:
    if st.session_state.get("live_stop_event"):
        st.session_state.live_stop_event.set()
    st.session_state.live_running = False
    for key in (
        "live_input_q", "live_output_q", "live_stop_event",
        "live_mute_event", "live_thread", "live_last_frame_id",
    ):
        st.session_state.pop(key, None)


def _drain_output_queue() -> str:
    """Pull all pending transcription chunks from the output queue."""
    output_q: queue.Queue = st.session_state.live_output_q
    new_text = ""
    while True:
        try:
            chunk = output_q.get_nowait()
            if isinstance(chunk, str):
                new_text += chunk
        except queue.Empty:
            break
    return new_text

# ── AUTO-START: open live session the moment this page loads ──────────────────
if not st.session_state.live_running:
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
# CAMERA BUTTON & IMAGE CAPTURE
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="camera-button-container">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    # Use a custom container for better styling
    captured = st.camera_input(
        "📷",
        key="camera_input",
        label_visibility="collapsed",
    )
st.markdown('</div>', unsafe_allow_html=True)

if captured is not None:
    frame_id = id(captured)
    if frame_id != st.session_state.get("live_last_frame_id"):
        st.session_state.live_last_frame_id = frame_id
        st.session_state.captured_image = captured.getvalue()
        # Push image into the live session so the AI can see it
        if st.session_state.live_running:
            st.session_state.live_input_q.put(
                {"type": "image", "data": st.session_state.captured_image}
            )

# Display captured image if available
if st.session_state.captured_image:
    st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
    img = st.image(
        st.session_state.captured_image,
        caption="Captured Document",
        use_container_width=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# AI RESPONSE DISPLAY SECTION
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="response-label">AI Analysis</div>', unsafe_allow_html=True)

# If we have captured image, analyze it
if st.session_state.captured_image and not st.session_state.ai_response:
    with st.spinner("🔍 Analyzing document..."):
        try:
            ai = CivicAI()
            context_text = get_context_block()
            response = ai.analyze_incident(
                image_bytes=st.session_state.captured_image,
                voice_text="Analyze this violation and provide every legal argument to fight this fine.",
                context_text=context_text if context_text else None,
            )
            st.session_state.ai_response = response
        except Exception as e:
            st.session_state.ai_response = f"❌ Analysis failed: {str(e)}"

# Display response in styled box
if st.session_state.ai_response:
    st.markdown(
        f'<div class="response-box">{st.session_state.ai_response}</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        '<div class="response-box" style="display: flex; align-items: center; justify-content: center; color: #707070;">Capture a document to begin analysis</div>',
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────────────────────────────────────
# TRANSCRIPT STREAMING SECTION
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="response-label">Live Transcript</div>', unsafe_allow_html=True)

# ── Status + Stop control ─────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    if st.session_state.live_running:
        st.markdown('<span class="status-badge status-recording">● Listening</span>', unsafe_allow_html=True)
with col2:
    if st.session_state.live_running:
        if st.button("⏹", key="stop_live", help="Stop session"):
            _stop_live_session()
            st.rerun()

# ── AI subtitle / transcript display ─────────────────────────────────────────
if st.session_state.live_running:
    transcript_container = st.empty()

    new_text = _drain_output_queue()
    if new_text:
        st.session_state.transcript = st.session_state.get("transcript", "") + new_text

    if st.session_state.transcript:
        transcript_container.markdown(
            f'<div class="transcript-box"><div class="transcription-live">{st.session_state.transcript}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        transcript_container.markdown(
            '<div class="transcript-box" style="color: #707070;">Listening — speak or take a photo...</div>',
            unsafe_allow_html=True,
        )

    # Auto-refresh to pull new transcription chunks
    time.sleep(0.5)
    st.rerun()
else:
    st.markdown(
        '<div class="transcript-box" style="color: #707070; border-left-color: #2a2a2a;">Session stopped.</div>',
        unsafe_allow_html=True,
    )

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
        st.session_state.ai_response = ""
        st.session_state.transcript = ""
        if st.session_state.live_running:
            _stop_live_session()
        st.switch_page("app.py")
st.markdown('</div>', unsafe_allow_html=True)
