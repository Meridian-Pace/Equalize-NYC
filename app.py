import time
import queue
import asyncio
import threading
import streamlit as st
from ai_engine import CivicAI
from live_engine import CivicAILive
from data_manager import get_context_block, load_rules

st.set_page_config(
    page_title="Equalize NYC",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("⚖️ Equalize NYC")
st.caption("A multimodal civic advocate for small businesses fighting municipal fines.")

# ─────────────────────────────────────────────────────────────────────────────
# Live session helpers (run in a background thread with its own event loop)
# ─────────────────────────────────────────────────────────────────────────────

async def _send_loop(
    engine: CivicAILive,
    input_q: queue.Queue,
    stop_event: threading.Event,
) -> None:
    """Drain the input queue and forward audio/image bytes to the live session."""
    while not stop_event.is_set():
        try:
            item = input_q.get_nowait()
            if item["type"] == "audio":
                await engine.send_audio(item["data"])
            elif item["type"] == "image":
                await engine.send_image(item["data"])
        except queue.Empty:
            await asyncio.sleep(0.05)


async def _receive_loop(
    engine: CivicAILive,
    output_q: queue.Queue,
    stop_event: threading.Event,
) -> None:
    """Forward every streamed chunk from the live session to the output queue."""
    async for chunk in engine.receive():
        if stop_event.is_set():
            break
        output_q.put(chunk)


async def _live_loop(
    engine: CivicAILive,
    input_q: queue.Queue,
    output_q: queue.Queue,
    stop_event: threading.Event,
) -> None:
    async with engine:
        await asyncio.gather(
            _send_loop(engine, input_q, stop_event),
            _receive_loop(engine, output_q, stop_event),
        )


def _run_live_thread(
    input_q: queue.Queue,
    output_q: queue.Queue,
    stop_event: threading.Event,
) -> None:
    """Entry point for the background thread — owns a dedicated event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    engine = CivicAILive()
    try:
        loop.run_until_complete(
            _live_loop(engine, input_q, output_q, stop_event)
        )
    finally:
        loop.close()


def _start_live_session() -> None:
    input_q: queue.Queue = queue.Queue()
    output_q: queue.Queue = queue.Queue()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_run_live_thread,
        args=(input_q, output_q, stop_event),
        daemon=True,
    )
    thread.start()
    st.session_state.live_running = True
    st.session_state.live_input_q = input_q
    st.session_state.live_output_q = output_q
    st.session_state.live_stop_event = stop_event
    st.session_state.live_thread = thread
    st.session_state.live_response = ""
    st.session_state.live_last_audio_id = None
    st.session_state.live_last_frame_id = None


def _stop_live_session() -> None:
    if st.session_state.get("live_stop_event"):
        st.session_state.live_stop_event.set()
    st.session_state.live_running = False
    for key in (
        "live_input_q", "live_output_q", "live_stop_event",
        "live_thread", "live_response",
        "live_last_audio_id", "live_last_frame_id",
    ):
        st.session_state.pop(key, None)


def _drain_output_queue() -> str:
    """Pull all pending chunks from the output queue into the response string."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────

tab_compliance, tab_live = st.tabs(["⚖️ Check Compliance", "🎙️ Live Session"])

# ── Tab 1: Check Compliance (original flow) ───────────────────────────────────

with tab_compliance:
    st.divider()

    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("📷 Visual Evidence")
        camera_image = st.camera_input("Capture the violation or fine notice")

    with right_col:
        st.subheader("🎙️ Your Question")
        audio_input = st.audio_input("Describe the situation or ask your question")

    st.divider()

    analyze_clicked = st.button(
        "⚖️ Check Compliance", type="primary", use_container_width=True
    )

    if analyze_clicked:
        image_bytes = camera_image.getvalue() if camera_image is not None else None
        voice_text = (
            "Analyze this violation and tell me every way I can fight this fine."
            if audio_input is not None
            else None
        )
        context_text = get_context_block()

        if image_bytes is None and voice_text is None and not context_text:
            st.warning("Please provide at least an image or audio input before analyzing.")
        else:
            with st.spinner("Consulting NYC compliance rules..."):
                try:
                    ai = CivicAI()
                    recommendation = ai.analyze_incident(
                        image_bytes=image_bytes,
                        voice_text=voice_text,
                        context_text=context_text if context_text else None,
                    )

                    st.success("Analysis complete.")

                    with st.expander("📜 Raw Legal Rule Context"):
                        raw_rules = load_rules()
                        if raw_rules:
                            st.text_area(
                                label="nyc_rules.txt",
                                value=raw_rules,
                                height=300,
                                disabled=True,
                            )
                        else:
                            st.info(
                                "No nyc_rules.txt found. Add one to provide compliance context."
                            )

                    st.subheader("AI Recommendation")
                    st.success(recommendation)

                except Exception as e:
                    st.error(f"Analysis failed: {e}")

# ── Tab 2: Live Session ────────────────────────────────────────────────────────

with tab_live:
    st.divider()

    live_running: bool = st.session_state.get("live_running", False)

    # ── Controls row ──────────────────────────────────────────────────────────
    ctrl_left, ctrl_right = st.columns([1, 1])

    with ctrl_left:
        if not live_running:
            if st.button("▶ Start Listening", type="primary", use_container_width=True):
                _start_live_session()
                st.rerun()
        else:
            st.success("Session active — AI is listening.")

    with ctrl_right:
        if live_running:
            if st.button("⏹ Stop Session", type="secondary", use_container_width=True):
                _stop_live_session()
                st.rerun()

    st.divider()

    # ── Audio + Camera inputs (only shown when session is running) ────────────
    if live_running:
        audio_col, frame_col = st.columns(2)

        with audio_col:
            st.subheader("🎙️ Stream Audio")
            live_audio = st.audio_input(
                "Speak your question — each recording is sent to the AI",
                key="live_audio_input",
            )

            if live_audio is not None:
                audio_id = id(live_audio)
                if audio_id != st.session_state.get("live_last_audio_id"):
                    st.session_state.live_last_audio_id = audio_id
                    st.session_state.live_input_q.put(
                        {"type": "audio", "data": live_audio.getvalue()}
                    )

        with frame_col:
            st.subheader("📷 Capture Frame")
            live_frame = st.camera_input(
                "Snap a frame to send mid-session",
                key="live_camera_input",
            )

            if live_frame is not None:
                frame_id = id(live_frame)
                if frame_id != st.session_state.get("live_last_frame_id"):
                    st.session_state.live_last_frame_id = frame_id
                    st.session_state.live_input_q.put(
                        {"type": "image", "data": live_frame.getvalue()}
                    )
                    st.caption("Frame sent to AI.")

        st.divider()

        # ── Streaming response display ────────────────────────────────────────
        st.subheader("AI Response")
        response_box = st.empty()

        new_text = _drain_output_queue()
        if new_text:
            st.session_state.live_response = (
                st.session_state.get("live_response", "") + new_text
            )

        accumulated = st.session_state.get("live_response", "")
        if accumulated:
            response_box.success(accumulated)
        else:
            response_box.info("Waiting for AI response...")

        # Auto-refresh every 500 ms while session is active
        time.sleep(0.5)
        st.rerun()

    else:
        st.info("Press **▶ Start Listening** to open a live AI session.")
