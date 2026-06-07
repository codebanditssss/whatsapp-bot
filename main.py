"""FastAPI webhook that Twilio calls on every incoming WhatsApp message."""
from fastapi import FastAPI, Request, Response, BackgroundTasks
from twilio.twiml.messaging_response import MessagingResponse

from bot import handle_message
from store import upsert_lead
from notify import alert_broker

app = FastAPI(title="WhatsApp Real Estate Bot")


def _has_info(lead: dict) -> bool:
    """True once the lead has shared anything worth logging."""
    return any(lead.get(k) for k in ("intent", "area", "budget", "property_type", "timeline"))


@app.get("/")
def health():
    return {"status": "ok", "bot": "gurgaon-realestate"}


@app.post("/whatsapp")
async def whatsapp(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    from_number = form.get("From", "")
    body = (form.get("Body") or "").strip()
    print(f"[in] {from_number}: {body}")

    reply, lead, just_booked = handle_message(from_number, body)
    print(f"[out] {from_number}: {reply}")

    # Log/refresh the lead row live — in the background so the reply isn't delayed.
    if _has_info(lead):
        background_tasks.add_task(upsert_lead, from_number, lead)
    if just_booked:
        background_tasks.add_task(alert_broker, lead, from_number)

    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")
