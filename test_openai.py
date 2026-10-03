import os
from dotenv import load_dotenv
from openai import OpenAI

# Load variables from .env
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL")

if not api_key:
    print("❌ OPENAI_API_KEY not found in .env")
    exit()

if not model:
    print("❌ OPENAI_MODEL not found in .env")
    exit()

print("🔄 Connecting to OpenAI...")
print(f"Model: {model}")

try:
    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=model,
        input="What is 2 + 2? Answer in one short sentence."
    )

    print("\n" + "=" * 50)
    print("✅ OPENAI API IS WORKING")
    print("=" * 50)
    print("Response:")
    print(response.output_text)
    print("=" * 50)

except Exception as e:
    print("\n❌ OPENAI API ERROR")
    print("-" * 50)
    print(type(e).__name__)
    print(str(e))