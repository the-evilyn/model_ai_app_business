from __future__ import annotations

import time

import requests

from chatbot_config import (
    LLM_MAX_TOKENS,
    LLM_REASONING_BUDGET,
    LLM_STREAM,
    LLM_TIMEOUT_SECONDS,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    is_llm_configured,
)
from llm_client import generate_llm_response


def _check_models_endpoint() -> None:
    url = f"{NVIDIA_BASE_URL.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        print(f"Models endpoint status: HTTP {response.status_code}")
        if response.status_code >= 400:
            print("Models endpoint error preview:", response.text[:400])
    except Exception as exc:
        print(f"Models endpoint check failed: {exc}")


def main() -> None:
    if not is_llm_configured():
        print("NVIDIA LLM is not configured. Check NVIDIA_API_KEY, NVIDIA_BASE_URL and NVIDIA_MODEL.")
        return

    print(
        "NVIDIA LLM configured: "
        f"base_url={NVIDIA_BASE_URL}, "
        f"model={NVIDIA_MODEL}, "
        f"key_set={bool(NVIDIA_API_KEY)}, "
        f"stream={LLM_STREAM}, "
        f"max_tokens={LLM_MAX_TOKENS}, "
        f"reasoning_budget={LLM_REASONING_BUDGET}, "
        f"timeout={LLM_TIMEOUT_SECONDS}s"
    )
    _check_models_endpoint()
    start = time.perf_counter()
    result = generate_llm_response(
        "You are a concise assistant. Always provide a final answer in the message content.",
        "Say exactly this as your final answer: NVIDIA connection works.",
    )
    elapsed = time.perf_counter() - start
    print(f"Elapsed: {elapsed:.2f}s")
    if result.get("reasoning_details"):
        print("Reasoning:")
        print(result["reasoning_details"])
    answer = result.get("response_text") or ""
    print(answer or "[No final content returned by the model]")


if __name__ == "__main__":
    main()
