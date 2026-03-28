# Equalize NYC — AI-Powered Civic Advocate for Small Businesses

A multimodal AI app that helps NYC small business owners fight back against municipal fines. Snap a photo of a violation notice, speak your question, and get an aggressive, legally-grounded defense strategy in seconds — powered by Google Gemini on Vertex AI.

## Purpose

NYC issues thousands of fines to small businesses every year. Many are procedurally flawed, misapplied, or outright bogus — but most owners pay them anyway because they don't know their rights or can't afford a lawyer.

Equalize NYC puts a predatory fine advocate in your pocket. It:

- Analyzes violation photos and audio questions with multimodal AI
- Cross-references NYC compliance rules to find every possible defense
- Supports real-time voice conversation so you can ask follow-up questions naturally
- Works in any language — responds in Spanish, English, or whatever the user speaks

## Features

- **Check Compliance tab** — upload a photo of a fine or violation notice, record your question, and get a detailed written legal defense
- **Live Session tab** — open a live voice session directly in the browser (Streamlit audio)
- **Terminal voice chat** (`chat_live.py`) — full duplex mic-to-speaker conversation with barge-in support and auto-reconnect
- **NYC Rules context** — drop a `nyc_rules.txt` file in the project root and the AI will cite specific rules in every response

## Getting Started

### Prerequisites

- Python 3.11+
- A GCP project with Vertex AI enabled
- A service account `credentials.json` with Vertex AI permissions

### Installation

Clone the repository:
```bash
git clone https://github.com/Meridian-Pace/Equalize-NYC.git
cd Equalize-NYC
```

Install dependencies:
```bash
pip install streamlit google-genai python-dotenv sounddevice numpy
```

Set up environment variables (copy the example and fill in your project ID):
```bash
cp .env.example .env
```

`.env` contents:
```
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=global
GCP_LIVE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
```

### Running the App

**Streamlit UI:**
```bash
python -m streamlit run app.py
```

**Terminal voice chat:**
```bash
python chat_live.py
```

**API smoke test (no mic needed):**
```bash
python test_live.py
```

**Auth check:**
```bash
python test_auth.py
```

## Project Structure

```
Equalize-NYC/
├── app.py               # Streamlit UI — Check Compliance + Live Session tabs
├── ai_engine.py         # Batch multimodal AI (photo + text → written defense)
├── live_engine.py       # Real-time BidiGenerateContent WebSocket session
├── data_manager.py      # Loads nyc_rules.txt as compliance context
├── config.py            # Environment variable loading and validation
├── chat_live.py         # Standalone terminal voice chat (mic → AI → speakers)
├── test_live.py         # Debug script: text question → streamed audio response
├── test_auth.py         # Minimal Vertex AI connectivity check
├── nyc_rules.txt        # NYC compliance rules (add your own — not committed)
├── credentials.json     # GCP service account key (gitignored)
├── .env                 # Local config (gitignored)
├── .env.example         # Template for .env
├── CODEBASE.md          # Full technical reference for all modules and APIs
└── README.md            # This file
```

## Technology Stack

- **Frontend:** Streamlit
- **AI:** Google Gemini on Vertex AI (`google-genai` 2026 SDK)
- **Batch model:** `gemini-3-flash-preview` — multimodal text + image analysis
- **Live model:** `gemini-live-2.5-flash-native-audio` — real-time bidirectional audio
- **Audio I/O:** `sounddevice` (terminal), `st.audio_input` (browser)

## License

Built for the NYC Build With AI Hackathon 2026 Hackathon.

## Team

**Meridian Pace** — NYC Build With AI Hackathon 2026

- Eric Kouperman — eric.kouperman@gmail.com
- Jacqueline Wong — winnie.yun.wong@gmail.com
- Nyosha Homicil — nyoshahomicil@gmail.com
- Alexander Westfal — alexcwestfal@gmail.com
