import os
import asyncio
from google import genai
from google.genai import types
from typing import AsyncIterator
import config

SYSTEM_PROMPT = """You are a legal advocate for NYC small business owners fighting municipal violations.

SILENCE RULE — HIGHEST PRIORITY: Output zero audio when this session starts. Do not speak, do not greet, do not say a single word until the user speaks first. Wait in complete silence. Your first audio output must be a direct reply to something the user said.
EXCEPTION TO SILENCE RULE: If [RESUMING INTERRUPTED SESSION] appears in your context, the previous session was cut off mid-response. Resume speaking immediately — do not wait for the user to speak first.

When the user describes a violation or asks about a photo, give them every legal argument and procedural defense to fight it — be specific and complete. Never cut yourself off mid-sentence.
If [Photo on file] appears in your context, do NOT mention it until the user asks about it.
Keep responses concise unless the user asks for detail.

LANGUAGE RULE: Always respond in the exact same language the user speaks. Never switch languages unless the user does first."""

LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    output_audio_transcription=types.AudioTranscriptionConfig(),
    system_instruction=types.Content(
        role="system",
        parts=[types.Part.from_text(text=SYSTEM_PROMPT)],
    ),
)


class CivicAILive:
    def __init__(self, photo_context: str = "", conv_history: str = ""):
        config.validate()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.CREDENTIALS_PATH
        self.client = genai.Client(
            vertexai=True,
            project=config.PROJECT_ID,
            location=config.LIVE_LOCATION,
        )
        self.model = "gemini-live-2.5-flash-native-audio"
        self._session = None
        self._cm = None

        # Build system instruction — inject photo and/or conversation history
        prompt = SYSTEM_PROMPT
        if photo_context:
            prompt += f"\n\n[Photo on file]\n{photo_context}"
        if conv_history:
            prompt += f"\n\n[RESUMING INTERRUPTED SESSION — continue naturally from where the session was cut off. Do NOT re-introduce yourself. Resume the conversation immediately.]\n{conv_history}"
        self._config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=types.Content(
                role="system",
                parts=[types.Part.from_text(text=prompt)],
            ),
        )

    async def start_session(self) -> None:
        """Open a persistent BidiGenerateContent websocket session."""
        self._cm = self.client.aio.live.connect(
            model=self.model,
            config=self._config,
        )
        self._session = await self._cm.__aenter__()

    async def send_text(self, text: str) -> None:
        """Send a text turn into the live session and signal turn_complete."""
        if self._session is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        await self._session.send(
            input=types.LiveClientContent(
                turns=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
                turn_complete=True,
            )
        )

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Stream a raw audio chunk into the live session."""
        if self._session is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        await self._session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[
                    types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                ]
            )
        )

    async def send_image(self, image_bytes: bytes) -> None:
        """Send a JPEG frame into the live session mid-stream."""
        if self._session is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        await self._session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[
                    types.Blob(data=image_bytes, mime_type="image/jpeg")
                ]
            )
        )

    async def receive_turn(self) -> AsyncIterator[str | bytes]:
        """Yield chunks for the current turn only, stopping at turn_complete.

        Yields:
            str  — transcription text (from output_audio_transcription)
            bytes — raw PCM audio chunk
        """
        if self._session is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        from google.genai import errors as _errors
        try:
            async for message in self._session.receive():
                if message.data is not None:
                    yield message.data
                server_content = getattr(message, "server_content", None)
                if server_content is not None:
                    for part in getattr(server_content, "output_transcription", []) or []:
                        if getattr(part, "text", None):
                            yield part.text
                if getattr(server_content, "turn_complete", False):
                    break
        except _errors.APIError as exc:
            code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if code != 1000:   # 1000 = normal websocket close
                raise

    async def receive(self) -> AsyncIterator[str | bytes | None]:
        """Yield audio chunks, transcription text, and turn-complete sentinels.

        Yields:
            bytes — raw PCM audio chunk
            str   — AI transcription text
            None  — turn_complete: AI has finished this response turn
        """
        if self._session is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        from google.genai import errors as _errors
        try:
            async for message in self._session.receive():
                if message.data is not None:
                    yield message.data
                server_content = getattr(message, "server_content", None)
                if server_content is not None:
                    for part in getattr(server_content, "output_transcription", []) or []:
                        if getattr(part, "text", None):
                            yield part.text
                    if getattr(server_content, "turn_complete", False):
                        yield None  # sentinel: AI finished speaking this turn
        except _errors.APIError as exc:
            code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if code != 1000:
                raise

    async def close(self) -> None:
        """Tear down the live session cleanly, tolerating already-dead sockets."""
        cm = self._cm
        # Clear references first so a double-close is a no-op
        self._cm = None
        self._session = None
        if cm is not None:
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                pass  # socket already closed by server — nothing to do

    # ------------------------------------------------------------------ #
    # Context-manager support for use with `async with CivicAILive() as ai`
    # ------------------------------------------------------------------ #
    async def __aenter__(self) -> "CivicAILive":
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
