from datetime import date

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"sent", "paid"},
    "sent": {"paid", "overdue"},
    "overdue": {"paid"},
    "paid": set(),
}


def can_transition(current: str, target: str) -> bool:
    if current == target:
        return True
    return target in ALLOWED_TRANSITIONS.get(current, set())


def effective_status(stored_status: str, due_date_iso: str, today: date | None = None) -> str:
    """
    Derive display status without mutating stored data.
    Non-paid invoices past due_date are effectively overdue.
    """
    if stored_status == "paid":
        return "paid"
    today = today or date.today()
    due = date.fromisoformat(due_date_iso)
    if due < today:
        return "overdue"
    return stored_status
