import os
import asyncio
from google import genai
from google.genai import types
from typing import AsyncIterator
import config

SYSTEM_PROMPT = """You are a predatory fine advocate for small businesses in NYC.
Your job is to find every possible legal argument, loophole, and procedural defense
to fight municipal fines and violations. Be aggressive, specific, and cite exact rules.
If the city issued a fine, assume it can be challenged until proven otherwise.

CRITICAL: Always respond in the exact same language the user speaks.
If they speak Spanish, respond entirely in Spanish.
If they speak English, respond entirely in English.
Never switch languages unless the user does first."""

LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    output_audio_transcription=types.AudioTranscriptionConfig(),
    system_instruction=types.Content(
        role="system",
        parts=[types.Part.from_text(text=SYSTEM_PROMPT)],
    ),
)


class CivicAILive:
    def __init__(self):
        config.validate()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.CREDENTIALS_PATH
        self.client = genai.Client(
            vertexai=True,
            project=config.PROJECT_ID,
            location=config.LIVE_LOCATION,
        )
        self.model = "gemini-live-2.5-flash-native-audio"
        self._session = None
        self._cm = None  # holds the context-manager returned by live.connect()

    async def start_session(self) -> None:
        """Open a persistent BidiGenerateContent websocket session."""
        self._cm = self.client.aio.live.connect(
            model=self.model,
            config=LIVE_CONFIG,
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
            if exc.status_code != 1000:   # 1000 = normal websocket close
                raise

    async def receive(self) -> AsyncIterator[str | bytes]:
        """Yield audio chunks and transcription text indefinitely (persistent session).

        Yields:
            str  — transcription text
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
        except _errors.APIError as exc:
            if exc.status_code != 1000:
                raise

    async def close(self) -> None:
        """Tear down the live session cleanly."""
        if self._cm is not None:
            await self._cm.__aexit__(None, None, None)
            self._cm = None
            self._session = None

    # ------------------------------------------------------------------ #
    # Context-manager support for use with `async with CivicAILive() as ai`
    # ------------------------------------------------------------------ #
    async def __aenter__(self) -> "CivicAILive":
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
