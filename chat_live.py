"""
chat_live.py — Real-time voice chat with the Equalize NYC AI.

Speak into your mic. The AI responds through your speakers.
Press Ctrl+C to end the session.

Requires: pip install sounddevice numpy
"""
import sys
import io
import asyncio
import queue
import threading

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    print("Missing dependency.  Run:  pip install sounddevice numpy")
    raise SystemExit(1)

import config
from live_engine import CivicAILive

# ── Audio constants ────────────────────────────────────────────────────────────
MIC_RATE     = 16_000   # Hz — Gemini Live input requirement
SPEAKER_RATE = 24_000   # Hz — gemini-live-2.5-flash-native-audio output
CHANNELS     = 1
DTYPE        = "int16"
MIC_CHUNK    = 1_024    # frames per block (~64 ms at 16 kHz)

_stop        = threading.Event()
speaker_q: queue.Queue = queue.Queue()


# ── Mic capture ────────────────────────────────────────────────────────────────
def _start_mic(loop: asyncio.AbstractEventLoop, mic_q: asyncio.Queue) -> sd.InputStream:
    chunks_sent = 0

    def _callback(indata: np.ndarray, frames, time_info, status) -> None:
        nonlocal chunks_sent
        if _stop.is_set():
            return
        loop.call_soon_threadsafe(mic_q.put_nowait, indata.tobytes())
        chunks_sent += 1

    stream = sd.InputStream(
        samplerate=MIC_RATE, channels=CHANNELS, dtype=DTYPE,
        blocksize=MIC_CHUNK, callback=_callback,
    )
    stream.start()
    return stream


# ── Speaker playback ───────────────────────────────────────────────────────────
def _speaker_worker() -> None:
    import traceback
    try:
        with sd.RawOutputStream(
            samplerate=SPEAKER_RATE, channels=CHANNELS, dtype=DTYPE,
        ) as stream:
            print(f"  [spk]  output stream open @ {SPEAKER_RATE} Hz", flush=True)
            while True:
                try:
                    chunk = speaker_q.get(timeout=0.5)
                    if chunk is None:
                        break
                    stream.write(chunk)
                except queue.Empty:
                    if _stop.is_set():
                        break
    except Exception:
        print("\n  [spk]  ERROR opening output stream:", flush=True)
        traceback.print_exc()
        # Drain the queue so receive_loop doesn't block forever
        while not speaker_q.empty():
            try:
                speaker_q.get_nowait()
            except queue.Empty:
                break


# ── Async send loop ────────────────────────────────────────────────────────────
async def _send_loop(engine: CivicAILive, mic_q: asyncio.Queue) -> None:
    while True:
        chunk = await mic_q.get()
        if chunk is None:
            return
        await engine.send_audio(chunk)


# ── Async receive loop (persistent) ───────────────────────────────────────────
async def _receive_loop(engine: CivicAILive) -> None:
    """Receive indefinitely. On turn_complete just stay open — VAD handles barge-in."""
    from google.genai import errors as _errors
    try:
        async for message in engine._session.receive():
            if _stop.is_set():
                return

            if message.data is not None:
                speaker_q.put(message.data)

            sc = getattr(message, "server_content", None)
            if sc is not None:
                for part in getattr(sc, "output_transcription", []) or []:
                    txt = getattr(part, "text", None)
                    if txt:
                        print(f"  {txt}", flush=True)
                if getattr(sc, "turn_complete", False):
                    print("\n  Listening...", flush=True)
                    # Stay open — mic keeps streaming for next turn

    except _errors.APIError as exc:
        if exc.status_code != 1000:
            raise
        # 1000 = server closed cleanly; propagate so run() can reconnect


# ── Main ───────────────────────────────────────────────────────────────────────
async def run() -> None:
    loop = asyncio.get_running_loop()
    mic_q: asyncio.Queue[bytes | None] = asyncio.Queue()

    spk_thread = threading.Thread(target=_speaker_worker, daemon=True)
    spk_thread.start()

    mic_stream = _start_mic(loop, mic_q)
    print("  Mic open.  Start talking — interrupt anytime.\n")

    try:
        while not _stop.is_set():
            try:
                async with CivicAILive() as ai:
                    print("\n  Listening...", flush=True)

                    send_task = asyncio.create_task(_send_loop(ai, mic_q))
                    recv_task = asyncio.create_task(_receive_loop(ai))

                    done, pending = await asyncio.wait(
                        {send_task, recv_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                    for task in done:
                        exc = task.exception()
                        if exc:
                            raise exc

            except (asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as exc:
                if _stop.is_set():
                    break
                print(f"  Reconnecting... ({exc.__class__.__name__})", flush=True)
                await asyncio.sleep(1)

    finally:
        _stop.set()
        mic_stream.stop()
        mic_stream.close()
        loop.call_soon_threadsafe(mic_q.put_nowait, None)
        speaker_q.put(None)
        spk_thread.join(timeout=3)
        print("\n  Session closed.\n")


# ── Mic level check ────────────────────────────────────────────────────────────
def mic_check(seconds: int = 4) -> bool:
    print(f"  Testing mic for {seconds}s — make some noise...\n")
    peak_overall = 0

    def _callback(indata: np.ndarray, frames, time_info, status) -> None:
        nonlocal peak_overall
        level = int(np.abs(indata).max())
        peak_overall = max(peak_overall, level)
        bars = int(level / 32768 * 40)
        bar = ("\u2588" * bars).ljust(40)
        print(f"\r  [{bar}] {level:5d}", end="", flush=True)

    with sd.InputStream(
        samplerate=MIC_RATE, channels=CHANNELS, dtype=DTYPE,
        blocksize=MIC_CHUNK, callback=_callback,
    ):
        sd.sleep(seconds * 1000)

    print(f"\n\n  Peak level: {peak_overall} / 32767")
    if peak_overall < 200:
        print("  No signal — check your mic in Windows Sound Settings.")
        return False
    print("  Mic OK.\n")
    return True


if __name__ == "__main__":
    config.validate()

    print("\n── Equalize NYC — Live Voice Chat ──────────────────────────────")
    print("  Persona : Predatory fine advocate for NYC small businesses")
    print("  Model   : gemini-live-2.5-flash-native-audio")
    print("  Tip     : Use headphones to prevent mic feedback")
    print("────────────────────────────────────────────────────────────────\n")

    if not mic_check():
        raise SystemExit(1)

    # Show device info so we can spot sample-rate mismatches
    out_dev = sd.query_devices(kind="output")
    in_dev  = sd.query_devices(kind="input")
    print(f"  Mic     : {in_dev['name']}  (default rate {int(in_dev['default_samplerate'])} Hz)")
    print(f"  Speaker : {out_dev['name']}  (default rate {int(out_dev['default_samplerate'])} Hz)")
    print(f"  Sending : {MIC_RATE} Hz  |  Receiving : {SPEAKER_RATE} Hz\n")

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n  Interrupted.\n")
