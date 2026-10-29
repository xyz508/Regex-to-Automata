"""Friday's tools: what Claude can actually do for you.

Every tool here is local and safe. Friday NEVER moves money by itself:
`prepare_payment` only builds a UPI / payment link that YOU tap and approve
with your PIN in your own payment app.
"""

from datetime import date, datetime, timedelta
from urllib.parse import quote, urlparse

import store

# ---------- tool definitions sent to Claude ----------

TOOLS = [
    {
        "name": "get_datetime",
        "description": "Get the current local date, time and weekday.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "remember",
        "description": "Save a lasting fact about the user (preferences, people, goals, habits). "
        "Use when the user says 'remember', or shares something clearly worth keeping.",
        "input_schema": {
            "type": "object",
            "properties": {"fact": {"type": "string", "description": "One short fact."}},
            "required": ["fact"],
            "additionalProperties": False,
        },
    },
    {
        "name": "forget",
        "description": "Delete a saved memory by its id.",
        "input_schema": {
            "type": "object",
            "properties": {"memory_id": {"type": "string"}},
            "required": ["memory_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_memories",
        "description": "List everything saved about the user, with ids.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "add_task",
        "description": "Add a task or reminder. 'due' is optional local time in ISO format "
        "(YYYY-MM-DDTHH:MM). Call get_datetime first if you need today's date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "due": {"type": "string", "description": "YYYY-MM-DDTHH:MM, or omit"},
            },
            "required": ["title"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_tasks",
        "description": "List open tasks and reminders (with ids), soonest first.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "complete_task",
        "description": "Mark a task done (removes it from the open list).",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "add_bill",
        "description": "Track a recurring monthly bill or payment (rent, electricity, phone, "
        "subscription, EMI). upi_id is the payee's UPI ID (like name@okbank) if they take UPI; "
        "pay_url is a website where it's paid. Both optional.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "amount": {"type": "number", "description": "Usual amount, 0 if it varies"},
                "currency": {"type": "string", "description": "Like INR or USD. Default INR."},
                "due_day": {"type": "integer", "description": "Day of month it's due, 1-31"},
                "upi_id": {"type": "string"},
                "payee_name": {"type": "string"},
                "pay_url": {"type": "string"},
            },
            "required": ["name", "amount", "due_day"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_bills",
        "description": "List tracked bills with days until due and whether this month's is paid.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "remove_bill",
        "description": "Stop tracking a bill.",
        "input_schema": {
            "type": "object",
            "properties": {"bill_id": {"type": "string"}},
            "required": ["bill_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "mark_bill_paid",
        "description": "Record that this month's payment for a bill is done. Only call this "
        "after the user confirms they actually paid.",
        "input_schema": {
            "type": "object",
            "properties": {"bill_id": {"type": "string"}},
            "required": ["bill_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "prepare_payment",
        "description": "Show the user a Pay button for a tracked bill. It opens their own UPI "
        "app (GPay, PhonePe, Paytm...) or the bill's website, pre-filled. The user approves "
        "with their own PIN. You cannot pay by yourself; never claim you did.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bill_id": {"type": "string"},
                "amount": {"type": "number", "description": "Override amount, e.g. this month's actual bill"},
            },
            "required": ["bill_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "open_link",
        "description": "Show the user a button that opens a website or app link.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full https:// URL"},
                "label": {"type": "string", "description": "Short button text"},
            },
            "required": ["url", "label"],
            "additionalProperties": False,
        },
    },
]

# Anthropic-hosted web search: runs on Anthropic's side, no code needed here.
SERVER_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}]


# ---------- helpers ----------

def _now() -> datetime:
    return datetime.now()


def _month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def _due_date(due_day: int, today: date) -> date:
    """This month's due date, clamped to the month's last day (e.g. 31 -> 30 in Nov)."""
    first_next = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_day = (first_next - timedelta(days=1)).day
    return today.replace(day=min(max(due_day, 1), last_day))


def bill_status(bill: dict, today: date | None = None) -> dict:
    today = today or _now().date()
    due = _due_date(bill["due_day"], today)
    paid = _month_key(today) in bill.get("paid_months", [])
    return {
        "id": bill["id"],
        "name": bill["name"],
        "amount": bill["amount"],
        "currency": bill.get("currency", "INR"),
        "due_date": due.isoformat(),
        "days_left": (due - today).days,  # negative = overdue
        "paid_this_month": paid,
    }


def due_alerts(within_days: int = 3) -> list[str]:
    """Plain-English alerts for unpaid bills and tasks due soon. Used by the UI poller."""
    data = store.read()
    alerts = []
    for bill in data["bills"]:
        s = bill_status(bill)
        if s["paid_this_month"]:
            continue
        if s["days_left"] < 0:
            alerts.append(f"{s['name']} bill is overdue by {-s['days_left']} days.")
        elif s["days_left"] <= within_days:
            when = "today" if s["days_left"] == 0 else f"in {s['days_left']} days"
            alerts.append(f"{s['name']} bill of {s['amount']:g} {s['currency']} is due {when}.")
    now = _now()
    for t in data["tasks"]:
        if t.get("done") or not t.get("due"):
            continue
        try:
            due = datetime.fromisoformat(t["due"])
        except ValueError:
            continue
        if due <= now + timedelta(hours=1):
            alerts.append(f"Reminder: {t['title']}" + (" (overdue)" if due < now else ""))
    return alerts


def _safe_url(url: str) -> bool:
    return urlparse(url).scheme in ("https", "http", "upi")


# ---------- execution ----------

def run_tool(name: str, args: dict, actions: list) -> str:
    """Execute a tool. UI buttons (pay / open link) are appended to `actions`."""
    if name == "get_datetime":
        return _now().strftime("%A %d %B %Y, %H:%M")

    if name == "remember":
        def add(d):
            m = {"id": store.new_id(), "fact": args["fact"].strip(), "saved": _now().isoformat(timespec="minutes")}
            d["memories"].append(m)
            return m
        m = store.update(add)
        return f"Saved (id {m['id']})."

    if name == "forget":
        def rm(d):
            before = len(d["memories"])
            d["memories"] = [m for m in d["memories"] if m["id"] != args["memory_id"]]
            return before != len(d["memories"])
        return "Deleted." if store.update(rm) else "No memory with that id."

    if name == "list_memories":
        mems = store.read()["memories"]
        return "\n".join(f"[{m['id']}] {m['fact']}" for m in mems) or "Nothing saved yet."

    if name == "add_task":
        due = args.get("due")
        if due:
            try:
                datetime.fromisoformat(due)
            except ValueError:
                raise ValueError("due must look like 2026-11-02T18:30")
        def add(d):
            t = {"id": store.new_id(), "title": args["title"].strip(), "due": due, "done": False}
            d["tasks"].append(t)
            return t
        t = store.update(add)
        return f"Task added (id {t['id']})."

    if name == "list_tasks":
        tasks = [t for t in store.read()["tasks"] if not t.get("done")]
        tasks.sort(key=lambda t: t.get("due") or "9999")
        return "\n".join(
            f"[{t['id']}] {t['title']}" + (f" - due {t['due']}" if t.get("due") else "") for t in tasks
        ) or "No open tasks."

    if name == "complete_task":
        def done(d):
            for t in d["tasks"]:
                if t["id"] == args["task_id"]:
                    t["done"] = True
                    return True
            return False
        return "Done." if store.update(done) else "No task with that id."

    if name == "add_bill":
        if not 1 <= args["due_day"] <= 31:
            raise ValueError("due_day must be 1-31")
        if args.get("pay_url") and not _safe_url(args["pay_url"]):
            raise ValueError("pay_url must start with https://")
        def add(d):
            b = {
                "id": store.new_id(),
                "name": args["name"].strip(),
                "amount": float(args["amount"]),
                "currency": (args.get("currency") or "INR").upper(),
                "due_day": int(args["due_day"]),
                "upi_id": (args.get("upi_id") or "").strip(),
                "payee_name": (args.get("payee_name") or args["name"]).strip(),
                "pay_url": (args.get("pay_url") or "").strip(),
                "paid_months": [],
            }
            d["bills"].append(b)
            return b
        b = store.update(add)
        return f"Tracking {b['name']} (id {b['id']}), due on day {b['due_day']} each month."

    if name == "list_bills":
        bills = [bill_status(b) for b in store.read()["bills"]]
        bills.sort(key=lambda s: s["days_left"])
        return "\n".join(
            f"[{s['id']}] {s['name']}: {s['amount']:g} {s['currency']}, due {s['due_date']} "
            f"({s['days_left']} days), {'PAID' if s['paid_this_month'] else 'unpaid'}"
            for s in bills
        ) or "No bills tracked."

    if name == "remove_bill":
        def rm(d):
            before = len(d["bills"])
            d["bills"] = [b for b in d["bills"] if b["id"] != args["bill_id"]]
            return before != len(d["bills"])
        return "Removed." if store.update(rm) else "No bill with that id."

    if name == "mark_bill_paid":
        def paid(d):
            for b in d["bills"]:
                if b["id"] == args["bill_id"]:
                    key = _month_key(_now().date())
                    if key not in b["paid_months"]:
                        b["paid_months"].append(key)
                    return b["name"]
            return None
        n = store.update(paid)
        return f"{n} marked paid for this month." if n else "No bill with that id."

    if name == "prepare_payment":
        bill = next((b for b in store.read()["bills"] if b["id"] == args["bill_id"]), None)
        if not bill:
            return "No bill with that id."
        amount = args.get("amount") or bill["amount"]
        if bill.get("upi_id"):
            url = (
                f"upi://pay?pa={quote(bill['upi_id'])}&pn={quote(bill['payee_name'])}"
                f"&cu={quote(bill.get('currency', 'INR'))}&tn={quote(bill['name'] + ' via Friday')}"
            )
            if amount:
                url += f"&am={amount:.2f}"
            actions.append({"type": "link", "label": f"Pay {bill['name']} ({amount:g})", "url": url})
            return "Pay button shown. It opens their UPI app; they enter their own PIN."
        if bill.get("pay_url"):
            actions.append({"type": "link", "label": f"Pay {bill['name']}", "url": bill["pay_url"]})
            return "Pay button shown, opens the bill's website."
        return "This bill has no UPI ID or pay website saved. Ask the user for one."

    if name == "open_link":
        if not _safe_url(args["url"]):
            raise ValueError("Only http(s) links are allowed.")
        actions.append({"type": "link", "label": args["label"][:60], "url": args["url"]})
        return "Link button shown."

    raise ValueError(f"Unknown tool {name}")
