"""
eval.py

Evaluation pipeline for the agent. Runs scripted questions from
eval_cases.json, records which tools the model called, and checks the
dollar amounts in each answer. Makes real API requests.

Usage:
    python eval.py --label baseline
    python eval.py --label after --only goal_remaining bills_week
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

from openai import APIError

import agent

PROJECT_DIR = Path(__file__).resolve().parent
CASES_FILE = PROJECT_DIR / "eval_cases.json"
RESULTS_DIR = PROJECT_DIR / "eval_results"

# matches 1,026.99 or 278.63 or 50
NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?")


def extract_amounts(text: str) -> list[float]:
    """Pull every number out of an answer, ignoring $ and thousands commas."""
    return [float(match.replace(",", "")) for match in NUMBER_PATTERN.findall(text)]


def check_tools(expected: list[str], called: list[str]) -> bool:
    """Pass if any expected tool was called, or no tools when none are expected."""
    if not expected:
        return not called
    return any(name in called for name in expected)


def check_answer(case: dict, answer: str) -> bool:
    """Pass if every expected amount appears and the keyword rule holds."""
    found = extract_amounts(answer)
    for amount in case.get("amounts", []):
        if not any(abs(amount - value) < 0.005 for value in found):
            return False

    keywords = case.get("keywords", [])
    if keywords:
        text = answer.lower().replace("’", "'")
        matches = [keyword in text for keyword in keywords]
        if not (all(matches) if case.get("all_keywords") else any(matches)):
            return False
    return True


def run_case(case: dict) -> dict:
    """Ask one question with a fresh history and score the result."""
    called = []
    original_execute_tool = agent.execute_tool

    # wrap execute_tool so we can see which tools the model chose
    def recording_execute_tool(name, arguments):
        called.append(name)
        return original_execute_tool(name, arguments)

    agent.execute_tool = recording_execute_tool
    try:
        answer = agent.run_agent(case["question"])
        error = None
    except APIError:
        # quota/network problems are not the agent's fault, stop the whole run
        raise
    except Exception as exc:
        answer, error = "", f"{type(exc).__name__}: {exc}"
    finally:
        agent.execute_tool = original_execute_tool

    tools_ok = error is None and check_tools(case["tools"], called)
    answer_ok = error is None and check_answer(case, answer)
    return {
        "id": case["id"],
        "question": case["question"],
        "expected_tools": case["tools"],
        "called_tools": called,
        "answer": answer,
        "error": error,
        "tools_ok": tools_ok,
        "answer_ok": answer_ok,
        "passed": tools_ok and answer_ok,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score the Balance agent on scripted questions.")
    parser.add_argument("--label", default="run", help="name saved with the results, e.g. baseline")
    parser.add_argument("--only", nargs="*", help="case ids to run (default: all)")
    args = parser.parse_args()

    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    if args.only:
        cases = [case for case in cases if case["id"] in args.only]

    results = []
    for case in cases:
        result = run_case(case)
        results.append(result)
        mark = "PASS" if result["passed"] else "FAIL"
        tools = ", ".join(result["called_tools"]) or "none"
        print(f"[{mark}] {case['id']:<26} tools: {tools}")
        if not result["passed"]:
            print(f"       answer: {result['error'] or result['answer']}")

    total = len(results)
    tool_score = sum(r["tools_ok"] for r in results)
    answer_score = sum(r["answer_ok"] for r in results)
    passed = sum(r["passed"] for r in results)
    print(f"\nTool selection: {tool_score}/{total}")
    print(f"Answer accuracy: {answer_score}/{total}")
    print(f"Overall passed: {passed}/{total} ({passed / total:.0%})")

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = RESULTS_DIR / f"{args.label}-{timestamp}.json"
    output.write_text(json.dumps({
        "label": args.label,
        "timestamp": timestamp,
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "summary": {
            "total": total,
            "tool_selection": tool_score,
            "answer_accuracy": answer_score,
            "passed": passed,
        },
        "results": results,
    }, indent=2), encoding="utf-8")
    print(f"Saved {output.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
