import os
from google import genai # This is the new 2026 SDK

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
PROJECT_ID = "gcloud-hackathon-yaueo3935unlm"

try:
    # This Client handles the 'global' routing much better for Gemini 3
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents="Ping!"
    )
    print(f"✅ SUCCESS: {response.text}")
except Exception as e:
    print(f"❌ STILL FAILING: {e}")
    print("TIP: If it says 'location unsupported', try location='us-east4'")