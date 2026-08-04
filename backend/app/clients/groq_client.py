"""Minimal Groq chat-completions client.

Groq exposes an OpenAI-compatible endpoint, so this is a single POST rather
than an SDK dependency. Only JSON-mode completions are needed here.
"""

import json

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqError(Exception):
    """Groq was unreachable, or returned something unusable."""


class GroqNotConfigured(GroqError):
    """No API key is set, so the feature cannot run at all."""


async def complete_json(
    system: str,
    user: str,
    api_key: str | None,
    model: str,
    timeout: float = 40.0,
) -> dict:
    """Ask Groq for a JSON object and return it parsed."""
    if not api_key:
        raise GroqNotConfigured(
            "GROQ_API_KEY is not set. Add it to backend/.env to enable daily plans."
        )

    payload = {
        "model": model,
        # JSON mode: the model is constrained to emit a single JSON object, so
        # the response never needs stripping of prose or code fences.
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
    except httpx.RequestError as e:
        raise GroqError(f"Could not reach Groq: {e}") from e

    if response.status_code == 401:
        raise GroqNotConfigured("Groq rejected the API key. Check GROQ_API_KEY.")
    if response.status_code == 429:
        raise GroqError("Groq rate limit reached. Try again shortly.")
    if response.status_code >= 400:
        raise GroqError(f"Groq returned HTTP {response.status_code}: {response.text[:200]}")

    try:
        body = response.json()
        content = body["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as e:
        raise GroqError("Groq returned an unexpected response shape") from e

    try:
        parsed = json.loads(content)
    except ValueError as e:
        raise GroqError("Groq did not return valid JSON") from e

    if not isinstance(parsed, dict):
        raise GroqError("Groq returned JSON that is not an object")
    return parsed
