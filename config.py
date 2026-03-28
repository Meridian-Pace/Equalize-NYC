import os
from pathlib import Path

# ── Load from a .env file if present (no-op if python-dotenv isn't installed) ──
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ID: str = os.environ.get("GCP_PROJECT_ID", "")
LOCATION: str = os.environ.get("GCP_LOCATION", "global")
# Live (BidiGenerateContent websocket) requires a regional endpoint, not "global"
LIVE_LOCATION: str = os.environ.get("GCP_LIVE_LOCATION", "us-central1")
CREDENTIALS_PATH: str = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(Path(__file__).parent / "credentials.json"),
)


def validate() -> None:
    """Raise ValueError with a fix hint if any required config is missing."""
    errors: list[str] = []

    if not PROJECT_ID:
        errors.append(
            "GCP_PROJECT_ID is not set.\n"
            "  Fix: add GCP_PROJECT_ID=your-project-id to your .env file."
        )

    if not LOCATION:
        errors.append(
            "GCP_LOCATION is not set.\n"
            "  Fix: add GCP_LOCATION=global to your .env file."
        )

    if not CREDENTIALS_PATH:
        errors.append(
            "GOOGLE_APPLICATION_CREDENTIALS is not set.\n"
            "  Fix: add GOOGLE_APPLICATION_CREDENTIALS=credentials.json to your .env file."
        )
    elif not Path(CREDENTIALS_PATH).is_file():
        errors.append(
            f"GOOGLE_APPLICATION_CREDENTIALS points to a file that does not exist: '{CREDENTIALS_PATH}'\n"
            "  Fix: place your service-account credentials.json at that path,\n"
            "       or update GOOGLE_APPLICATION_CREDENTIALS in your .env file."
        )

    if errors:
        raise ValueError(
            "Equalize NYC — configuration error(s):\n\n"
            + "\n\n".join(f"  [{i+1}] {e}" for i, e in enumerate(errors))
        )
