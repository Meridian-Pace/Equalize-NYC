import os
import vertexai
from vertexai.generative_models import GenerativeModel

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
PROJECT_ID = "gcloud-hackathon-yaueo3935unlm"

try:
    vertexai.init(project=PROJECT_ID, location="global")
    model = GenerativeModel("gemini-3-flash-preview") 
    
    response = model.generate_content("Ping!")
    print("-" * 30)
    print(f"SUCCESS: {response.text}")
    print("-" * 30)
except Exception as e:
    print(f"❌ ERROR: {e}")
# dont forget to run with python test_auth.py - alex