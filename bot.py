"""The brain: one Gemini call per message that returns BOTH the reply to send
and the structured lead data we extracted so far.

We ask Gemini for JSON: {"reply": "...", "lead": {...}, "stage": "..."}.
Only `reply` is sent to the user. `lead` + `stage` are used internally to
decide when a lead is qualified and a visit is booked.
"""
import json
import time

import config

B = config.BROKER

# ---- LLM clients (lazy: only build the one we use) ----
if config.LLM_PROVIDER == "openai":
    from openai import OpenAI
    _oai = OpenAI(api_key=config.OPENAI_API_KEY)
    print(f"[bot] brain: OpenAI ({config.OPENAI_MODEL})")
else:
    from google import genai
    from google.genai import types
    _genai = genai.Client(api_key=config.GEMINI_API_KEY)
    print(f"[bot] brain: Gemini ({config.GEMINI_MODEL})")

SYSTEM_PROMPT = f"""
You are the WhatsApp assistant for {B['agency_name']}, a real estate brokerage in
{B['city']}. The human agent is {B['agent_name']}. You chat with leads who message
on WhatsApp and your ONE job is to qualify them and book a site visit.

ABOUT THE BUSINESS (only talk about this; never invent other areas or services):
- Areas served: {', '.join(B['areas'])}
- Property types: {', '.join(B['property_types'])}
- Typical budget range: {B['budget_range']}

HOW TO TALK:
- Warm, brief, human. WhatsApp style — short messages, 1-3 lines. No corporate fluff.
- The lead may write in English, Hindi, or Hinglish. Reply in whatever they use.
- Ask ONE question at a time. Never interrogate with a list.
- If they ask something off-topic or about an area you don't serve, gently steer back.

QUALIFY before booking. You must naturally collect: {', '.join(B['qualify_fields'])}.
Once you have those, propose a site visit and offer 2 simple time options
(e.g. "tomorrow evening" or "this weekend"). When the lead agrees to a visit and a
rough time, the lead is BOOKED — confirm warmly and tell them {B['agent_name']} will
call to finalise.

OUTPUT FORMAT — respond with ONLY valid JSON, no markdown, exactly:
{{
  "reply": "<the WhatsApp message to send the lead>",
  "lead": {{
    "name": "<lead's name or empty>",
    "intent": "<buy / rent / empty>",
    "area": "<area they want or empty>",
    "budget": "<budget or empty>",
    "property_type": "<type or empty>",
    "timeline": "<when they want to move/buy or empty>",
    "visit_time": "<agreed visit time or empty>"
  }},
  "stage": "<one of: greeting | qualifying | booking | booked>"
}}
Set stage to "booked" ONLY when the lead has agreed to a site visit AND a rough time.
Carry forward any lead info already known from earlier in the conversation.
""".strip()

if config.LLM_PROVIDER == "gemini":
    _gen_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.6,
        # Disable "thinking" — cuts reply latency hard (WhatsApp needs to feel instant).
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

# In-memory sessions keyed by WhatsApp number. Fine for a demo; swap for Redis later.
_sessions: dict[str, dict] = {}


def _empty_lead() -> dict:
    return {
        "name": "", "intent": "", "area": "", "budget": "",
        "property_type": "", "timeline": "", "visit_time": "",
    }


# Gemini models tried in order if the primary is briefly overloaded.
_GEMINI_MODELS = [config.GEMINI_MODEL, "gemini-flash-latest"]
_TRANSIENT = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded",
              "high demand", "Connection", "Timeout", "timeout")


def _raw_call(prompt: str, model_idx: int) -> str:
    """One LLM call → raw JSON string. Provider-agnostic."""
    if config.LLM_PROVIDER == "openai":
        resp = _oai.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.6,
        )
        return resp.choices[0].message.content
    model = _GEMINI_MODELS[min(model_idx, len(_GEMINI_MODELS) - 1)]
    resp = _genai.models.generate_content(
        model=model, contents=prompt, config=_gen_config
    )
    return resp.text


def _call_gemini(prompt: str, attempts: int = 4) -> dict:
    """Call the LLM with retry + backoff on transient errors."""
    last_err = None
    for i in range(attempts):
        try:
            return json.loads(_raw_call(prompt, i))
        except Exception as e:  # noqa: BLE001
            last_err = e
            if any(t in str(e) for t in _TRANSIENT) and i < attempts - 1:
                wait = 0.7 * (i + 1)
                print(f"[bot] transient error, retry in {wait}s ({i+1}/{attempts})")
                time.sleep(wait)
                continue
            raise
    raise last_err


def handle_message(from_number: str, user_text: str):
    """Returns (reply_text, lead_dict, just_booked: bool)."""
    sess = _sessions.setdefault(
        from_number, {"history": [], "lead": _empty_lead(), "stage": "greeting"}
    )

    sess["history"].append(f"Lead: {user_text}")
    transcript = "\n".join(sess["history"][-20:])
    known = json.dumps(sess["lead"], ensure_ascii=False)

    prompt = (
        f"Lead info known so far: {known}\n\n"
        f"Conversation so far:\n{transcript}\n\n"
        "Reply to the lead's latest message. Respond with JSON only."
    )

    try:
        data = _call_gemini(prompt)
        reply = (data.get("reply") or "").strip()
        new_lead = {**sess["lead"], **(data.get("lead") or {})}
        new_stage = data.get("stage", sess["stage"])
    except Exception as e:  # noqa: BLE001 - never crash the webhook
        print(f"[bot] gemini error after retries: {e}")
        reply = "Sorry, I had a hiccup 😅 could you say that once more?"
        new_lead, new_stage = sess["lead"], sess["stage"]

    just_booked = new_stage == "booked" and sess["stage"] != "booked"

    sess["history"].append(f"Assistant: {reply}")
    sess["lead"] = new_lead
    sess["stage"] = new_stage

    return reply, new_lead, just_booked
