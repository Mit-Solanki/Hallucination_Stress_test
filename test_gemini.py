import os
from dotenv import load_dotenv
from google import genai

# Load variables from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env")
    exit()

if not model:
    print("❌ GEMINI_MODEL not found in .env")
    exit()

print("🔄 Connecting to Gemini...")
print(f"Model: {model}")

try:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents="What is 2 + 2? Answer in one short sentence."
    )

    print("\n" + "=" * 50)
    print("✅ GEMINI API IS WORKING")
    print("=" * 50)
    print("Response:")
    print(response.text)
    print("=" * 50)

except Exception as e:
    print("\n❌ GEMINI API ERROR")
    print("-" * 50)
    print(type(e).__name__)
    print(str(e))