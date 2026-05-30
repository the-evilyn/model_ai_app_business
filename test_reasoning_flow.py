from __future__ import annotations

from llm_client import generate_llm_response


def main() -> None:
    result = generate_llm_response(
        "You are a concise reasoning assistant.",
        "How many r's are in the word 'strawberry'? Answer briefly.",
    )
    print(result.get("response_text", ""))


if __name__ == "__main__":
    main()
