import os
from dotenv import load_dotenv
from google import genai

# Load the .env file so we can read GEMINI_API_KEY
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

# Create a client using our API key
client = genai.Client(api_key=api_key)

# Send a simple test message
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="Say hello in one short sentence."
)

print("Gemini responded:")
print(response.text)