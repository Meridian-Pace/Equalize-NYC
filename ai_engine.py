import os
import json
import tempfile

import google.genai as genai
from google.genai import types


MODEL_NAME = "gemini-3-flash-preview"
LOCATION = "global"


def _project_id_from_credentials(credentials_path: str) -> str | None:
    try:
        with open(credentials_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data.get("project_id")
    except Exception:
        return None


def _resolve_credentials() -> tuple[str | None, str | None]:
    """Use Streamlit secrets in cloud, then fall back to local credentials.json."""
    try:
        import streamlit as st

        service_account = st.secrets.get("GCP_SERVICE_ACCOUNT")
        if service_account:
            if isinstance(service_account, str):
                service_account_data = json.loads(service_account)
            else:
                service_account_data = dict(service_account)

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                encoding="utf-8",
                delete=False,
            ) as temp_file:
                json.dump(service_account_data, temp_file)
                credentials_path = temp_file.name

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            return credentials_path, service_account_data.get("project_id")
    except Exception:
        pass

    credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    if os.path.exists(credentials_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        return credentials_path, _project_id_from_credentials(credentials_path)

    return None, os.environ.get("GCP_PROJECT_ID")


def get_analysis(image_bytes: bytes, user_query: str, legal_context: str) -> str:
    """Analyze evidence and question using NYC legal context as primary authority."""
    _, project_id = _resolve_credentials()

    client = genai.Client(
        vertexai=True,
        project=project_id or os.environ.get("GCP_PROJECT_ID"),
        location=LOCATION,
    )

    system_prompt = """You are a Civic Advocate for NYC small businesses.
Use the provided legal context as the primary source of truth.
If information is missing from the legal context, say so clearly.
Explain likely violations, practical defenses, and immediate corrective steps.
Be specific, structured, and non-alarmist."""

    parts = [
        types.Part.from_text(
            f"NYC Legal Context (Primary Source of Truth):\n{legal_context or 'No legal context provided.'}"
        ),
        types.Part.from_text(f"User Question:\n{user_query}"),
    ]

    if image_bytes:
        parts.insert(1, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            max_output_tokens=2048,
        ),
    )

    return (response.text or "No analysis returned.").strip()
