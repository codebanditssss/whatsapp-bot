"""Central config + the per-broker settings.

For each new client you onboard, the ONLY thing you edit is the BROKER dict
below (name, areas, budget range, property types, agent number, the questions).
Everything else stays the same. Those recurring fields are exactly what becomes
the admin panel later.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ---- Secrets / infra (from .env) ----
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# OpenAI (optional). If a real API key is set, the bot uses OpenAI instead of Gemini.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Auto-pick provider: OpenAI if a key is present, else Gemini.
LLM_PROVIDER = "openai" if (OPENAI_API_KEY and "sk-" in OPENAI_API_KEY) else "gemini"
BROKER_WHATSAPP = os.getenv("BROKER_WHATSAPP", "").strip()

# ---- Google Sheets (the CRM) ----
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# ---- The one broker this bot is set up for (edit per client) ----
BROKER = {
    "agency_name": "Gurgaon Prime Realty",
    "agent_name": "Rahul",
    "agent_phone": "+91 98XXX XXXXX",
    "city": "Gurgaon",
    "areas": [
        "Golf Course Road",
        "Golf Course Extension Road",
        "Sohna Road",
        "DLF Phase 1-5",
        "New Gurgaon (Sectors 81-95)",
        "MG Road",
    ],
    "property_types": ["Apartments / Flats", "Builder Floors", "Plots", "Commercial"],
    "budget_range": "₹80 lakh to ₹6 crore",
    # The qualification fields the bot must collect before booking a visit.
    "qualify_fields": ["intent (buy/rent)", "area/locality", "budget", "timeline"],
}
