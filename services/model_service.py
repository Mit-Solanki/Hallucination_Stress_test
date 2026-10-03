import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from google.genai import types

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

_openai_client = None
_gemini_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment")
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client

def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment")
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client

def load_prompt(version: str) -> str:
    """
    Load system prompt by version: 'v1', 'v2', or 'v3'.
    Maps to prompts/basic.txt, prompts/fact_check.txt, prompts/defensive.txt.
    """
    mapping = {
        "v1": "prompts/basic.txt",
        "v2": "prompts/fact_check.txt",
        "v3": "prompts/defensive.txt"
    }
    v_key = version.lower()
    if v_key not in mapping:
        raise ValueError(f"Unknown prompt version: {version}. Expected v1, v2, or v3.")
    
    prompt_file = Path(mapping[v_key])
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read().strip()

import time

def call_model(model_name: str, system_prompt: str, user_prompt: str, max_retries: int = 5) -> str:
    """
    Execute call to specified model ('openai' or 'gemini').
    Fairness Rule: The exact same system_prompt and user_prompt are used for both models.
    """
    model_key = model_name.lower().strip()
    backoff_intervals = [3, 6, 10, 15, 20]
    
    for attempt in range(max_retries):
        try:
            if model_key in ["openai", "gpt"]:
                client = get_openai_client()
                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.choices[0].message.content or ""
                
            elif model_key in ["gemini", "google"]:
                client = get_gemini_client()
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt
                    )
                )
                return response.text or ""
                
            else:
                raise ValueError(f"Unsupported model: {model_name}. Allowed: 'openai', 'gemini'")
        except Exception as e:
            err_msg = str(e)
            # If daily quota exceeded or non-transient quota limit, do not retry - fail immediately
            if any(term in err_msg for term in ["Quota exceeded", "GenerateRequestsPerDay", "PerDay", "requests per day", "RPD", "Please try again in", "rate_limit_exceeded"]):
                raise e

            # If 503, 429, or transient network error, retry
            if attempt < max_retries - 1 and any(code in err_msg for code in ["503", "429", "UNAVAILABLE", "rate_limit", "timeout"]):
                wait_time = backoff_intervals[min(attempt, len(backoff_intervals) - 1)]
                print(f"[{model_key}] Transient error ({err_msg[:60]}...). Retrying in {wait_time}s (attempt {attempt+2}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise e
