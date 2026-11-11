# llm.py - one job: send a message to Gemini and return its answer.
import json
import os
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()  # reads GEMINI_API_KEY and GEMINI_MODEL from the .env file

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL")


def ask(prompt):
    # Gemini is sometimes busy (503) or the free limit is reached (429). Then wait and try again.
    for attempt in range(3):
        try:
            answer = client.models.generate_content(model=MODEL, contents=prompt)
            return answer.text
        except errors.APIError as error:
            if error.code not in (429, 503):
                raise
            print(f"   Gemini is busy (error {error.code}). Waiting 30 seconds...")
            time.sleep(30)
    raise SystemExit("Gemini is busy or your free limit is used up. Try again later.")


def ask_json(prompt):
    # Gemini often wraps JSON in ``` marks. Remove them, then read the JSON.
    text = ask(prompt).strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```")
    return json.loads(text)


if __name__ == "__main__":
    # Try it: python llm.py "Say hello in five words"
    print(ask(sys.argv[1] if len(sys.argv) > 1 else "Say hello in five words"))
