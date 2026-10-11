"""Unit tests for tools.py against the mock data in data/. No API requests."""

from tools import (
    get_accounts,
    get_budget,
    get_recent_transactions,
    get_safe_to_spend,
    get_savings_goals,
    get_spending,
    get_upcoming_expenses,
)


# existing tools

def test_accounts_total_includes_savings():
    result = get_accounts()
    assert result["total_balance_cents"] == 166000
    assert len(result["accounts"]) == 2


def test_recent_transactions_newest_first():
    result = get_recent_transactions(limit=2)
    assert [t["merchant"] for t in result["transactions"]] == ["Uniqlo", "Starbucks"]


def test_recent_transactions_rejects_bad_limit():
    assert "error" in get_recent_transactions(limit=0)


def test_spending_this_week_starts_monday():
    result = get_spending("dining", "this_week")
    assert result["start_date"] == "2026-09-21"
    assert result["spent_cents"] == 650


def test_budget_remaining():
    result = get_budget("Dining ")
    assert result["spent_cents"] == 2137
    assert result["remaining_cents"] == 27863


def test_budget_missing_category():
    assert "error" in get_budget("groceries")


# savings goals

def test_savings_goals_all():
    names = [goal["name"] for goal in get_savings_goals()["goals"]]
    assert names == ["Spring Break Trip", "Emergency Fund"]


def test_savings_goal_partial_name_match():
    goal = get_savings_goals("spring break")["goals"][0]
    assert goal["remaining_cents"] == 49000
    assert goal["months_left"] == 6
    assert goal["percent_complete"] == 18.3


def test_savings_goal_monthly_amount_rounds_up():
    # 49000 / 6 = 8166.67 -> 8167 so six payments always reach the target
    goal = get_savings_goals("spring")["goals"][0]
    assert goal["monthly_needed_cents"] == 8167
    assert goal["monthly_needed_cents"] * goal["months_left"] >= goal["remaining_cents"]


def test_savings_goal_not_found_lists_options():
    result = get_savings_goals("new car")
    assert "error" in result
    assert "Emergency Fund" in result["available_goals"]


# upcoming bills

def test_bills_next_seven_days():
    result = get_upcoming_expenses(7)
    assert [bill["name"] for bill in result["bills"]] == ["Phone Bill", "Spotify"]
    assert result["total_due_cents"] == 5699


def test_bills_default_thirty_days_excludes_later_bill():
    result = get_upcoming_expenses()
    assert result["bill_count"] == 4
    assert result["total_due_cents"] == 102699
    assert result["end_date"] == "2026-10-22"


def test_bills_window_includes_bill_on_end_date():
    # second phone bill is due 2026-10-25, exactly 33 days out
    assert get_upcoming_expenses(33)["bill_count"] == 5
    assert get_upcoming_expenses(32)["bill_count"] == 4


def test_bills_sorted_by_due_date():
    dates = [bill["due_date"] for bill in get_upcoming_expenses(60)["bills"]]
    assert dates == sorted(dates)


def test_bills_reject_bad_days():
    assert "error" in get_upcoming_expenses(0)
    assert "error" in get_upcoming_expenses(400)
    assert "error" in get_upcoming_expenses("30")


# safe to spend

def test_safe_to_spend_uses_checking_only():
    result = get_safe_to_spend()
    assert result["checking_balance_cents"] == 125000
    assert result["upcoming_bills_cents"] == 102699
    assert result["safe_to_spend_cents"] == 22301


def test_safe_to_spend_short_window():
    assert get_safe_to_spend(7)["safe_to_spend_cents"] == 125000 - 5699


def test_safe_to_spend_passes_through_errors():
    assert "error" in get_safe_to_spend(-1)
