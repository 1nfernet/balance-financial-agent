# Balance Financial Agent

A small Python prototype for Balance, our senior design budgeting assistant.
The project explores LLM tool calling: a model chooses a financial tool,
Python runs it against mock data, and the model explains the result.

The assistant is designed around everyday questions like "How much do I have
left for dining?", "What bills are due this week?", and "Can I afford a $300
jacket?" Python tools retrieve account balances, filter transactions, calculate
spending and remaining budgets, track savings goals, list upcoming bills, and
work out how much is safe to spend. Financial answers should come from those
results.

Everything uses fictional JSON data. There are no bank connections or money
transfers. Date based tools use September 22, 2026 as a fixed demo date.

## Run locally

Use Python 3.10 or newer. On macOS or Linux (bash/zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root with your API key:

```text
OPENAI_API_KEY=your_api_key_here
```

Then run:

```powershell
python main.py
```

Ask a financial question, or type `exit` to finish. Conversation history is kept in memory until you exit. Run `python main.py --verbose` to print each tool call and its result so you can see how the answer was produced.
An API key with available API quota is required to use the assistant.

Run `python tools.py` for local tool examples or `python data_access.py` to
inspect the mock records. These commands do not make API requests.

## Tools

| Tool | Answers |
|---|---|
| `get_accounts` | Account balances and combined total |
| `get_recent_transactions` | Latest purchases, optionally by category |
| `get_spending` | Spending for a category today, this week, this month, or last month |
| `get_budget` | Monthly limit, spent, and remaining for a category |
| `get_savings_goals` | Goal progress, remaining amount, and monthly amount needed |
| `get_upcoming_expenses` | Bills due in the next N days and their total |
| `get_safe_to_spend` | Checking balance minus bills due in the next N days |

If the model asks for an unknown tool or sends bad arguments, the error is sent
back to the model as the tool result so it can correct itself instead of the
whole request failing.

## Tests and evaluation

Unit tests use the mock data and a fake model client, so they make no API requests:

```bash
python -m pytest
```

`eval.py` runs the scripted questions in `eval_cases.json` through the real
model. Each case checks that an expected tool was called and that the expected
dollar amounts (or keywords) appear in the answer. Results are printed and saved
to `eval_results/`.

```bash
python eval.py --label after
python eval.py --only goal_remaining bills_week
```

Answers can vary between runs, so compare scores across a few runs.

## Project structure

- `data/`: fictional financial records stored as JSON.
- `data_access.py`: reads the JSON files.
- `tools.py`: filters records and calculates financial results.
- `agent.py`: the home for model instructions and tool-call orchestration.
- `main.py`: the interactive command-line interface.
- `eval.py`, `eval_cases.json`: evaluation pipeline and its test questions.
- `tests/`: pytest unit tests.

Amounts are stored in integer cents. Account balances are snapshots that already
include completed purchases; budget spending is calculated from transactions.
API keys belong in environment variables and must never be committed.
