"""
llm_client.py
-------------
NVIDIA-only LLM client for the NexusAI Business Chatbot, analysis
interpretation, and report content generation.

Secrets are read from environment variables through chatbot_config.py.
The API key is never logged or returned.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from chatbot_config import (
    LLM_MAX_TOKENS,
    LLM_REASONING_BUDGET,
    LLM_STREAM,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    LLM_TOP_P,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    is_llm_configured,
)

logger = logging.getLogger(__name__)



def _clean_model_content(text: str) -> str:
    """Keep only final user-visible content from NVIDIA responses."""
    cleaned = (text or "").strip()
    cleaned = re.sub(r"(?is)<think>.*?</think>", "", cleaned).strip()
    cleaned = re.sub(r"(?is)<reasoning>.*?</reasoning>", "", cleaned).strip()
    cleaned = re.sub(r"(?is)^\s*(reasoning|thinking|analysis)\s*:\s*.*?(final answer\s*:|answer\s*:)", "", cleaned).strip()
    cleaned = re.sub(r"(?im)^\s*(we need to|i need to|must use only|internal|system prompt|project context|api results|retrieved knowledge).*$", "", cleaned).strip()
    cleaned = re.sub(r"(?m)^\s*[\d\s.,-]{8,}\s*$", "", cleaned).strip()
    cleaned = cleaned.replace("Final answer:", "").replace("Answer:", "").strip()
    return cleaned
def get_llm_provider() -> dict[str, Any]:
    """Return the current NVIDIA LLM status without exposing secrets."""
    configured = is_llm_configured()
    return {
        "provider": "nvidia",
        "model": NVIDIA_MODEL,
        "configured": configured,
        "fallback_mode": not configured,
    }


def generate_llm_response(
    system_prompt: str,
    user_message: str,
    context: str = "",
    messages_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate text with NVIDIA, or return a structured fallback."""
    if not is_llm_configured():
        return _fallback_response(system_prompt, user_message, context)

    try:
        return _call_nvidia(system_prompt, user_message, context, messages_history)
    except Exception as exc:
        logger.error("NVIDIA LLM call failed: %s", exc)
        result = _fallback_response(system_prompt, user_message, context)
        result["error"] = f"NVIDIA LLM call failed: {exc}"
        return result


def generate_json_response(
    system_prompt: str,
    user_message: str,
    context: str = "",
) -> dict[str, Any]:
    """Generate a response expected to be JSON and parse it safely."""
    result = generate_llm_response(system_prompt, user_message, context)
    result["json"] = _parse_json_object(result.get("response_text", ""))
    return result


def _call_nvidia(
    system_prompt: str,
    user_message: str,
    context: str,
    messages_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call NVIDIA NIM through its OpenAI-compatible Chat Completions format."""
    url = f"{NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    if messages_history:
        messages = messages_history
    else:
        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({"role": "system", "content": f"Additional context:\n{context}"})
        messages.append({"role": "user", "content": user_message})

    payload = {
        "model": NVIDIA_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "top_p": LLM_TOP_P,
        "max_tokens": LLM_MAX_TOKENS,
        "stream": LLM_STREAM,
    }

    if "deepseek" in NVIDIA_MODEL.lower():
        payload["chat_template_kwargs"] = {"thinking": False}
    elif "nemotron-3-nano" in NVIDIA_MODEL.lower():
        payload["chat_template_kwargs"] = {"enable_thinking": True}
        if LLM_REASONING_BUDGET > 0:
            payload["reasoning_budget"] = LLM_REASONING_BUDGET

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        stream=LLM_STREAM,
        timeout=LLM_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    response_text, reasoning_details = (
        (_read_streaming_response(response), None)
        if LLM_STREAM
        else _read_json_response(response)
    )

    return {
        "response_text": response_text,
        "provider": "nvidia",
        "model": NVIDIA_MODEL,
        "fallback_mode": False,
        "error": None,
        "reasoning_details": reasoning_details,
    }


def _read_json_response(response: requests.Response) -> tuple[str, str | None]:
    data = response.json()
    message = data["choices"][0]["message"]
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content")
    return _clean_model_content(content), reasoning


def _read_streaming_response(response: requests.Response) -> str:
    chunks: list[str] = []
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if line.startswith("data:"):
            line = line[5:].strip()
        if line == "[DONE]":
            break
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        delta = data.get("choices", [{}])[0].get("delta", {})
        content = delta.get("content")
        if content:
            chunks.append(content)
    return _clean_model_content("".join(chunks))


def _parse_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(cleaned[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def _fallback_response(system_prompt: str, user_message: str, context: str) -> dict[str, Any]:
    """Return a useful structured response when NVIDIA is unavailable."""
    response_parts = [
        "## AI Business Advisor Response (Template Mode)\n",
        "**Note:** NVIDIA LLM is not configured or unavailable. ",
        "This response is generated from available API results and internal rules.\n",
        f"**Your question:** {user_message}\n",
    ]

    if context:
        ctx_preview = context[:2000] + ("..." if len(context) > 2000 else "")
        response_parts.append(f"\n**Available context:**\n{ctx_preview}\n")

    response_parts.append(
        "\nConfigure NVIDIA in `.env` for generated answers:\n"
        "```env\n"
        "NVIDIA_API_KEY=your_key_here\n"
        "NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1\n"
        "NVIDIA_MODEL=your_model_here\n"
        "```\n"
    )

    return {
        "response_text": "".join(response_parts),
        "provider": "nvidia",
        "model": "fallback_template",
        "fallback_mode": True,
        "error": None,
    }
