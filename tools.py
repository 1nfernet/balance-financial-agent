"""
tools.py

This file contains the tools that the financial agent I am 
building will have access to. For example, getting user
budgets, bank accoutn balances, transaction data, etc...
"""

from datetime import date, timedelta
from data_access import (
    load_accounts,
    load_budgets,
    load_savings_goals,
    load_transactions,
    load_upcoming_expenses,
)

# Fixed date for mock dataset, not curr date
DEMO_DATE = date(2026, 9, 22)

# Helper functions
def _period_start(period: str) -> date:
    """Find the inclusive start date; weeks begin on Monday."""

    if period == "today":
        return DEMO_DATE
    if period == "this_week":
        return DEMO_DATE - timedelta(days=DEMO_DATE.weekday())
    if period == "this_month":
        return DEMO_DATE.replace(day=1)
    if period == "last_month":
        return (DEMO_DATE.replace(day=1) - timedelta(days=1)).replace(day=1)
    
    raise ValueError("Use today, this_week, this_month, or last_month.")


def _months_until(deadline: date) -> int:
    """Count calendar months left before a deadline, at least one."""

    months = (deadline.year - DEMO_DATE.year) * 12 + deadline.month - DEMO_DATE.month
    return max(months, 1)


def _category_error(category: str) -> dict | None:
    """Recognize categories found in either budgets or transactions."""

    categories = set()
    for record in load_budgets():
        categories.add(record["category"])

    for record in load_transactions():
        categories.add(record["category"])

    if category not in categories:
        return {
            "error": f"Unknown category: {category}",
            "available_categories": sorted(categories),
        }
    return None

# Tools
def get_accounts() -> dict:
    """Return individual account balances and their combined total."""

    accounts = load_accounts()

    total_balance_cents = sum(
        account["balance_cents"] for account in accounts
    )

    return {
        "accounts": accounts,
        "total_balance_cents": total_balance_cents,
        "currency": "USD",
    }

def get_recent_transactions(category: str | None = None, limit: int = 5) -> dict:
    """Return the latest completed purchases, optionally filtered by category."""

    # check if limit of recent transaction is possible
    if type(limit) is not int or limit < 1:
        return {"error": "limit must be a positive integer."}

    # check if category exists if requested
    if category is not None:
        category = category.strip().lower()
        error = _category_error(category)
        if error:
            return error

    # get transactions and sort
    transactions = [
        transaction for transaction in load_transactions()
        if date.fromisoformat(transaction["date"]) <= DEMO_DATE
        and (category is None or transaction["category"] == category)
    ]
    transactions.sort(key=lambda transaction: transaction["date"], reverse=True)

    return {
        "transactions": transactions[:limit],
        "as_of_date": DEMO_DATE.isoformat(),
        "currency": "USD",
    }

def get_spending(category: str, period: str = "this_month") -> dict:
    """Sum recorded purchases within an inclusive date range."""

    category = category.strip().lower()
    error = _category_error(category)
    if error:
        return error

    try:
        start = _period_start(period)
    except ValueError as error:
        return {"error": str(error)}

    end = DEMO_DATE
    if period == "last_month":
        end = DEMO_DATE.replace(day=1) - timedelta(days=1)

    transactions = [
        transaction for transaction in load_transactions()
        if transaction["category"] == category
        and start <= date.fromisoformat(transaction["date"]) <= end
    ]
    return {
        "category": category,
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "spent_cents": sum(item["amount_cents"] for item in transactions),
        "transaction_count": len(transactions),
        "currency": "USD",
    }

def get_budget(category: str) -> dict:
    """Return this month's limit, recorded spending, and remaining budget."""
    category = category.strip().lower()
    month = DEMO_DATE.strftime("%Y-%m")
    budget = next(
        (item for item in load_budgets()
         if item["category"] == category and item["month"] == month),
        None,
    )
    if budget is None:
        return {"error": f"No budget found for {category} in {month}."}

    spending = get_spending(category, "this_month")
    if "error" in spending:
        return spending
    return {
        "category": category,
        "month": month,
        "as_of_date": DEMO_DATE.isoformat(),
        "limit_cents": budget["limit_cents"],
        "spent_cents": spending["spent_cents"],
        "remaining_cents": budget["limit_cents"] - spending["spent_cents"],
        "currency": "USD",
    }


def get_savings_goals(goal: str | None = None) -> dict:
    """Return savings goal progress and the monthly amount needed to finish on time."""

    goals = load_savings_goals()

    # match goal name loosely so "spring break" finds "Spring Break Trip"
    if goal is not None:
        query = goal.strip().lower()
        goals = [item for item in goals if query in item["name"].lower()]
        if not goals:
            return {
                "error": f"No savings goal matching {goal}.",
                "available_goals": [item["name"] for item in load_savings_goals()],
            }

    results = []
    for item in goals:
        deadline = date.fromisoformat(item["deadline"])
        remaining = max(item["target_cents"] - item["saved_cents"], 0)
        months_left = _months_until(deadline)
        results.append({
            "id": item["id"],
            "name": item["name"],
            "target_cents": item["target_cents"],
            "saved_cents": item["saved_cents"],
            "remaining_cents": remaining,
            "percent_complete": round(100 * item["saved_cents"] / item["target_cents"], 1),
            "deadline": item["deadline"],
            "days_left": (deadline - DEMO_DATE).days,
            "months_left": months_left,
            # round up so saving this much each month always reaches the goal
            "monthly_needed_cents": -(-remaining // months_left),
        })

    return {
        "goals": results,
        "as_of_date": DEMO_DATE.isoformat(),
        "currency": "USD",
    }

def get_upcoming_expenses(days: int = 30) -> dict:
    """Return bills due after the demo date and within the next number of days."""

    if type(days) is not int or not 1 <= days <= 365:
        return {"error": "days must be an integer from 1 to 365."}

    end = DEMO_DATE + timedelta(days=days)
    bills = [
        bill for bill in load_upcoming_expenses()
        if DEMO_DATE < date.fromisoformat(bill["due_date"]) <= end
    ]
    bills.sort(key=lambda bill: bill["due_date"])

    return {
        "bills": bills,
        "start_date": DEMO_DATE.isoformat(),
        "end_date": end.isoformat(),
        "total_due_cents": sum(bill["amount_cents"] for bill in bills),
        "bill_count": len(bills),
        "currency": "USD",
    }

def get_safe_to_spend(days: int = 30) -> dict:
    """Checking balance minus bills due in the window; savings are not counted."""

    upcoming = get_upcoming_expenses(days)
    if "error" in upcoming:
        return upcoming

    checking_cents = sum(
        account["balance_cents"] for account in load_accounts()
        if account["type"] == "checking"
    )
    return {
        "checking_balance_cents": checking_cents,
        "upcoming_bills_cents": upcoming["total_due_cents"],
        "safe_to_spend_cents": checking_cents - upcoming["total_due_cents"],
        "bill_count": upcoming["bill_count"],
        "end_date": upcoming["end_date"],
        "currency": "USD",
    }


if __name__ == "__main__":
    import json

    examples = {
        "Accounts": get_accounts(),
        "Recent purchases": get_recent_transactions(),
        "Dining this week": get_spending("dining", "this_week"),
        "Dining budget": get_budget("dining"),
        "Unknown category": get_budget("groceries"),
        "Savings goals": get_savings_goals(),
        "Bills next 7 days": get_upcoming_expenses(7),
        "Safe to spend (30 days)": get_safe_to_spend(),
    }
    for name, result in examples.items():
        print(f"\n{name}")
        print(json.dumps(result, indent=2))
