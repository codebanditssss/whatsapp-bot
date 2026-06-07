"""Talk to the bot in your terminal — no WhatsApp/Twilio needed.
Proves the Gemini brain + qualification flow work before you wire up the webhook.

    python chat_test.py

Type messages as if you were a lead. Ctrl+C to quit.
"""
from bot import handle_message
from store import log_lead

ME = "whatsapp:+910000000000"  # fake lead number for testing

print("💬 Chatting with the bot as a lead. (Ctrl+C to quit)\n")
try:
    while True:
        text = input("You (lead): ").strip()
        if not text:
            continue
        reply, lead, just_booked = handle_message(ME, text)
        print(f"Bot: {reply}\n")
        if just_booked:
            log_lead(ME, lead)
            print(f"✅ LEAD BOOKED & LOGGED: {lead}\n")
except KeyboardInterrupt:
    print("\nBye!")
