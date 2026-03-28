import os
import vertexai
from vertexai.generative_models import GenerativeModel

# 1. Point to the key you downloaded
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

# 2. Your Project ID (Look at your Google Cloud URL or Dashboard)
PROJECT_ID = "gcloud-hackathon-yaueo3935unlm" 

try:
    vertexai.init(project=PROJECT_ID, location="us-central1")
    model = GenerativeModel("gemini-1.5-flash")
    # Simple text test
    response = model.generate_content("Is the Equalize NYC engine online?")
    print("-" * 30)
    print(f"RESULT: {response.text}")
    print("-" * 30)
except Exception as e:
    print(f"❌ AUTH ERROR: {e}")