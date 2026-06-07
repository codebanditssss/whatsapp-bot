"""Lead logging → Google Sheets (your CRM).

If Sheets isn't reachable (no creds, network blip, etc.) we fall back to a local
CSV so a lead is NEVER silently lost during a live demo.
"""
import csv
import os
from datetime import datetime

import config

LEADS_FILE = os.path.join(os.path.dirname(__file__), "leads.csv")

FIELDS = [
    "timestamp", "phone", "name", "intent", "area",
    "budget", "property_type", "timeline", "visit_time",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_worksheet = None  # cached so we don't re-auth on every lead


def _row(phone: str, lead: dict) -> list:
    return [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        phone.replace("whatsapp:", ""),
        lead.get("name", ""),
        lead.get("intent", ""),
        lead.get("area", ""),
        lead.get("budget", ""),
        lead.get("property_type", ""),
        lead.get("timeline", ""),
        lead.get("visit_time", ""),
    ]


def _get_worksheet():
    global _worksheet
    if _worksheet is not None:
        return _worksheet
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(config.GOOGLE_SHEET_ID).sheet1
    if not ws.get_all_values():  # empty sheet → write header once
        ws.append_row(FIELDS)
    _worksheet = ws
    return ws


def _log_csv(phone: str, lead: dict) -> None:
    new_file = not os.path.exists(LEADS_FILE)
    with open(LEADS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(FIELDS)
        writer.writerow(_row(phone, lead))
    print(f"[store] logged lead to CSV ({LEADS_FILE})")


def upsert_lead(phone: str, lead: dict) -> None:
    """Create or update this lead's row (one row per phone), updating live as the
    conversation progresses. Called in the background so it never slows a reply."""
    if not config.GOOGLE_SHEET_ID:
        _log_csv(phone, lead)
        return
    try:
        ws = _get_worksheet()
        p = phone.replace("whatsapp:", "")
        cell = ws.find(p, in_column=2)  # phone lives in column B
        row = _row(phone, lead)
        if cell:
            ws.update(f"A{cell.row}:I{cell.row}", [row])
            print(f"[store] updated lead row {cell.row} ✅")
        else:
            ws.append_row(row)
            print("[store] new lead row added ✅")
    except Exception as e:  # noqa: BLE001 - never crash the webhook path
        print(f"[store] Sheets failed ({e}); falling back to CSV")
        _log_csv(phone, lead)


# Back-compat alias (used on final booking).
log_lead = upsert_lead
