This /data directory is meant to house mock data that will be used to test the financial agent and tool calls. 

All data will be stored in json files
Files:
- accounts.json: account snapshots (checking and savings balances).
- budgets.json: monthly category limits.
- transactions.json: completed purchases used to calculate spending.
- savings_goals.json: savings targets, saved amounts, and deadlines.
- upcoming_expenses.json: future bills and due dates. Only bills due after the demo date count as upcoming.

Conventions:
- Money uses integer cents: 1487 means $14.87.
- Dates use YYYY-MM-DD; budget months use YYYY-MM.
- Categories use consistent lowercase names, such as dining.
- Transactions currently represent completed purchases with positive amounts.
- Calculate spending and remaining budgets from transactions instead of storing them separately.
- Future bills do not count as completed spending.
- Relative dates such as today use the fixed DEMO_DATE (2026-09-22) in tools.py for a reproducible demo.

The initial records are a starting example, not a complete demo dataset.
