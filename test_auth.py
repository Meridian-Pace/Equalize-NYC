import os
from google import genai

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
PROJECT_ID = "gcloud-hackathon-yaueo3935unlm"

try:
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents="Ping!"
    )
    print(f"✅ SUCCESS: {response.text}")
except Exception as e:
    print(f"STILL FAILING: {e}")
    
    # python test_auth.py