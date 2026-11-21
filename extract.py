import base64
import os

import anthropic
from google import genai
from google.genai import types

from schema import Extraction

CLAUDE_MODEL = "claude-opus-5-5"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-4-hydrogen")
PROMPT = "Extract the data from this well drilling file."

SYSTEM = """You extract data from scanned well drilling files of the National Water Supply and \
Drainage Board, Sri Lanka. Each PDF covers one well and contains a handwritten Site Location Sheet \
(Format 011), a handwritten Drill Log (Format 031), typed pumping test reports, and letters or job cards.

Rules:
- Transcribe what is written; do not invent values. Use "" for blank boxes and for anything illegible.
- Printed option lists (e.g. YES / NO, funding criteria) are answered by striking out the options that \
do not apply or circling the one that does. Report the option that remains.
- When a handwritten value is struck out and replaced, report the replacement.
- The legend box at the foot of the Drill Log is printed on the form; it is not data.
- Pumping test reports often cover two wells. Extract only the values for this file's well \
(the Well No on the Site Location Sheet).
- Place names are Sri Lankan; prefer the spelling in typed pages when the handwriting is ambiguous."""


def _claude(pdf_bytes):
    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=32000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "high"},
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {
                    "type": "base64", "media_type": "application/pdf",
                    "data": base64.standard_b64encode(pdf_bytes).decode(),
                }},
                {"type": "text", "text": PROMPT},
            ],
        }],
        output_format=Extraction,
    ) as stream:
        message = stream.get_final_message()
    if message.stop_reason != "end_turn":
        raise RuntimeError(f"Extraction stopped early: {message.stop_reason}")
    return message.parsed_output, message.usage.input_tokens, message.usage.output_tokens


def _gemini(pdf_bytes):
    # Credentials come from the environment: GEMINI_API_KEY, or Vertex AI via
    # GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION.
    client = genai.Client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), PROMPT],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_schema=Extraction,
        ),
    )
    if response.parsed is None:
        raise RuntimeError("Gemini returned no parsable extraction")
    usage = response.usage_metadata
    return response.parsed, usage.prompt_token_count, usage.candidates_token_count + (usage.thoughts_token_count or 0)


PROVIDERS = {"claude": _claude, "gemini": _gemini}


def extract(pdf_bytes: bytes, provider: str):
    """Returns (Extraction, input_tokens, output_tokens)."""
    return PROVIDERS[provider](pdf_bytes)
