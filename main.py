"""
main.py

This file is the cli interface to call the agent.
"""

import argparse

from openai import APIError, AuthenticationError, RateLimitError
from agent import run_agent


# 429 codes that mean billing or spend limits, not sending requests too fast
QUOTA_ERROR_CODES = {
    "insufficient_quota",
    "credit_balance_exhausted",
    "organization_spend_limit_exceeded",
    "project_spend_limit_exceeded",
    "organization_usage_limit_exceeded",
}


def describe_rate_limit(error: RateLimitError) -> str:
    """Tell an empty account apart from sending requests too quickly."""
    code = getattr(error, "code", None)
    if code in QUOTA_ERROR_CODES or getattr(error, "type", None) == "insufficient_quota":
        return f"Balance: The API account is out of credit or over its spend limit ({code or 'insufficient_quota'}). Check Billing.\n"
    return "Balance: Too many requests right now (rate limit). Wait a moment and try again.\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the Balance financial assistant.")
    parser.add_argument("-v", "--verbose", action="store_true", help="print each tool call and its result")
    args = parser.parse_args()

    print("Balance Financial Assistant")
    print("Fictional demo data. Conversation is remembered until you exit.")
    print("Type exit or quit to finish.\n")

    history: list[dict] = []

    while True:
        try:
            message = input("You: ").strip()
            if message.lower() in {"exit", "quit"}:
                break
            if not message:
                continue

            try:
                answer = run_agent(message, history, verbose=args.verbose)
                print(f"Balance: {answer or 'No answer returned. Please try again.'}\n")
            except AuthenticationError:
                print("Balance: Authentication failed. Check OPENAI_API_KEY in .env.\n")
            except RateLimitError as error:
                print(describe_rate_limit(error))
            except APIError:
                print("Balance: The API request failed. Check your connection and try again.\n")
            except (ValueError, RuntimeError):
                print("Balance: Could not complete the request. Check your API key setup or try rephrasing.\n")
            except (OSError, KeyError, TypeError):
                print("Balance: Could not read or process the financial data. Check the local JSON files.\n")
        except (EOFError, KeyboardInterrupt):
            print()
            break

    print("Goodbye!")


if __name__ == "__main__":
    main()
