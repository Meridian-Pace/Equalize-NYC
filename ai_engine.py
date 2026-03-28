import google.genai as genai
from google.genai import types
import os

class CivicAI:
    def __init__(self, credentials_path: str = "credentials.json"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        self.client = genai.Client(
            vertexai=True,
            project=os.environ.get("GCP_PROJECT_ID"),
            location="global",
        )
        self.model = "gemini-3-flash-preview"

    def analyze_incident(
        self,
        image_bytes: bytes | None,
        voice_text: str | None,
        context_text: str | None,
    ) -> str:
        system_prompt = """You are a predatory fine advocate for small businesses in NYC.
Your job is to find every possible legal argument, loophole, and procedural defense
to fight municipal fines and violations. Be aggressive, specific, and cite exact rules.
If the city issued a fine, assume it can be challenged until proven otherwise."""

        parts = []

        if context_text:
            parts.append(
                types.Part.from_text(
                    f"NYC Compliance Rules Context:\n{context_text}"
                )
            )

        if image_bytes:
            parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            )

        user_query = voice_text or "Analyze this violation and tell me how to fight it."
        parts.append(types.Part.from_text(f"User Question: {user_query}"))

        response = self.client.models.generate_content(
            model=self.model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )

        return response.text
