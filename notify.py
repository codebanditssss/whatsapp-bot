"""Ping the broker on WhatsApp when a fresh lead books a visit."""
from twilio.rest import Client

import config

_client = None
if config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
    _client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)


def alert_broker(lead: dict, lead_phone: str) -> None:
    if not _client or not config.BROKER_WHATSAPP:
        print("[notify] broker alert skipped (no BROKER_WHATSAPP set)")
        return

    phone = lead_phone.replace("whatsapp:", "")
    msg = (
        "🔥 *New qualified lead!*\n\n"
        f"👤 {lead.get('name') or 'Unknown'}\n"
        f"📞 {phone}\n"
        f"🎯 {lead.get('intent', '')} · {lead.get('property_type', '')}\n"
        f"📍 {lead.get('area', '')}\n"
        f"💰 {lead.get('budget', '')}\n"
        f"🗓 Timeline: {lead.get('timeline', '')}\n"
        f"🏠 Visit: {lead.get('visit_time', '')}\n\n"
        "Call them to confirm 👆"
    )
    try:
        _client.messages.create(
            from_=config.TWILIO_WHATSAPP_FROM,
            to=config.BROKER_WHATSAPP,
            body=msg,
        )
        print("[notify] broker alerted")
    except Exception as e:  # noqa: BLE001
        print(f"[notify] failed to alert broker: {e}")
