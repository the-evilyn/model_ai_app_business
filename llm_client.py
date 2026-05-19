"""
llm_client.py
─────────────
External LLM client supporting OpenAI, Gemini, Mistral, Claude, and OpenRouter APIs.

Uses HTTP requests directly (no vendor SDK required) so that only `requests`
is needed as a dependency.  Falls back to structured template responses when
no API key is configured.

IMPORTANT:
- Does NOT use Ollama or any local LLM.
- All calls go to external cloud APIs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from chatbot_config import (
    CLAUDE_API_KEY,
    GEMINI_API_KEY,
    LLM_MAX_TOKENS,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    MISTRAL_API_KEY,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    get_effective_model,
    is_llm_configured,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════ #
#                         PUBLIC API                                        #
# ═══════════════════════════════════════════════════════════════════════════ #


def get_llm_provider() -> dict[str, Any]:
    """Return a dictionary describing the current LLM provider status."""
    provider = LLM_PROVIDER
    model = get_effective_model(provider)
    configured = is_llm_configured()
    return {
        "provider": provider,
        "model": model,
        "configured": configured,
        "fallback_mode": not configured,
    }


def generate_llm_response(
    system_prompt: str,
    user_message: str,
    context: str = "",
    messages_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send a prompt to the configured LLM provider and return the response.

    Returns
    -------
    dict with keys:
        - response_text: str   — the generated text
        - provider: str        — which provider was used
        - model: str           — which model was used
        - fallback_mode: bool  — whether a fallback was used
        - error: str | None    — error message if any
    """
    if not is_llm_configured():
        return _fallback_response(system_prompt, user_message, context)

    provider = LLM_PROVIDER
    try:
        if provider == "openai":
            return _call_openai(system_prompt, user_message, context)
        elif provider == "gemini":
            return _call_gemini(system_prompt, user_message, context)
        elif provider == "mistral":
            return _call_mistral(system_prompt, user_message, context)
        elif provider == "claude":
            return _call_claude(system_prompt, user_message, context)
        elif provider == "openrouter":
            return _call_openrouter(system_prompt, user_message, context, messages_history)
        else:
            logger.warning("Unknown LLM provider '%s', using fallback.", provider)
            return _fallback_response(system_prompt, user_message, context)
    except Exception as exc:
        logger.error("LLM call failed for provider '%s': %s", provider, exc)
        result = _fallback_response(system_prompt, user_message, context)
        result["error"] = f"LLM call failed: {exc}"
        return result


# ═══════════════════════════════════════════════════════════════════════════ #
#                       PROVIDER IMPLEMENTATIONS                            #
# ═══════════════════════════════════════════════════════════════════════════ #


def _call_openai(system_prompt: str, user_message: str, context: str) -> dict[str, Any]:
    """Call the OpenAI Chat Completions API."""
    model = get_effective_model("openai")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "system", "content": f"Additional context:\n{context}"})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    return {
        "response_text": data["choices"][0]["message"]["content"],
        "provider": "openai",
        "model": model,
        "fallback_mode": False,
        "error": None,
    }


def _call_gemini(system_prompt: str, user_message: str, context: str) -> dict[str, Any]:
    """Call the Google Gemini (Generative Language) API."""
    model = get_effective_model("gemini")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={GEMINI_API_KEY}"
    )
    headers = {"Content-Type": "application/json"}

    combined_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nUser question:\n{user_message}"

    payload = {
        "contents": [{"parts": [{"text": combined_prompt}]}],
        "generationConfig": {
            "temperature": LLM_TEMPERATURE,
            "maxOutputTokens": LLM_MAX_TOKENS,
        },
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return {
        "response_text": text,
        "provider": "gemini",
        "model": model,
        "fallback_mode": False,
        "error": None,
    }


def _call_mistral(system_prompt: str, user_message: str, context: str) -> dict[str, Any]:
    """Call the Mistral AI Chat API."""
    model = get_effective_model("mistral")
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "system", "content": f"Additional context:\n{context}"})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    return {
        "response_text": data["choices"][0]["message"]["content"],
        "provider": "mistral",
        "model": model,
        "fallback_mode": False,
        "error": None,
    }


def _call_claude(system_prompt: str, user_message: str, context: str) -> dict[str, Any]:
    """Call the Anthropic Messages API (Claude)."""
    model = get_effective_model("claude")
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    user_content = user_message
    if context:
        user_content = f"Context:\n{context}\n\nQuestion:\n{user_message}"

    payload = {
        "model": model,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    text_parts = [block["text"] for block in data["content"] if block.get("type") == "text"]
    return {
        "response_text": "\n".join(text_parts),
        "provider": "claude",
        "model": model,
        "fallback_mode": False,
        "error": None,
    }


def _call_openrouter(
    system_prompt: str,
    user_message: str,
    context: str,
    messages_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call the OpenRouter API (OpenAI-compatible at openrouter.ai)."""
    model = get_effective_model("openrouter")
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # If messages_history is provided, use it directly (it should contain system prompt too if needed)
    # Otherwise construct it
    if messages_history:
        messages = messages_history
    else:
        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({"role": "system", "content": f"Additional context:\n{context}"})
        messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "reasoning": {"enabled": True}
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    message_obj = data["choices"][0]["message"]
    return {
        "response_text": message_obj["content"],
        "provider": "openrouter",
        "model": model,
        "fallback_mode": False,
        "error": None,
        "reasoning_details": message_obj.get("reasoning_details"),
        "reasoning": message_obj.get("reasoning")
    }


# ═══════════════════════════════════════════════════════════════════════════ #
#                       FALLBACK (NO LLM KEY)                               #
# ═══════════════════════════════════════════════════════════════════════════ #


def _fallback_response(system_prompt: str, user_message: str, context: str) -> dict[str, Any]:
    """Generate a structured template response when no LLM API key is available.

    The response summarises the user question and the context provided so that
    it is still useful — just not LLM-generated.
    """
    response_parts = [
        "## AI Business Advisor Response (Template Mode)\n",
        "**Note:** No LLM API key is configured. This is a structured template response ",
        "based on the available API results and internal knowledge.\n",
        f"**Your question:** {user_message}\n",
    ]

    if context:
        # Truncate context if too long for display
        ctx_preview = context[:2000] + ("..." if len(context) > 2000 else "")
        response_parts.append(f"\n**Available context:**\n{ctx_preview}\n")

    response_parts.append(
        "\n**To get personalised AI-generated answers**, configure an LLM provider "
        "in your `.env` file:\n"
        "```\n"
        "LLM_PROVIDER=openai\n"
        "OPENAI_API_KEY=your_key_here\n"
        "LLM_MODEL=gpt-4o-mini\n"
        "```\n"
        "Supported providers: OpenAI, Gemini, Mistral, Claude, OpenRouter.\n"
    )

    return {
        "response_text": "".join(response_parts),
        "provider": "none",
        "model": "fallback_template",
        "fallback_mode": True,
        "error": None,
    }
