"""
Gemini LLM integration.

IMPORTANT: the legacy `google-generativeai` SDK (and the gemini-1.5-* models
it defaults to) has been shut down by Google. This service uses the current
unified `google-genai` SDK (`pip install google-genai`) talking to
`gemini-2.5-flash` by default (see app/config.py to change the model).

If GEMINI_API_KEY is not set, every function below degrades gracefully to a
deterministic, template-based explanation instead of throwing -- the app
stays fully usable (just less chatty) without a key configured.
"""

from typing import Optional

from google import genai

from app.config import GEMINI_API_KEY, GEMINI_MODEL

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _call_gemini(prompt: str) -> str:
    """Single-shot text generation. Raises on failure (caller decides fallback)."""
    response = _get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    text = (response.text or "").strip()
    if not text:
        raise ValueError("Gemini returned an empty response")
    return text


def generate_outfit_explanation(
    user_message: str,
    outfit_data: dict,
    gender: Optional[str],
    occasion: Optional[str],
) -> str:
    """Ask Gemini to turn a curated outfit + stylist note into a warm, personalised explanation."""
    if not GEMINI_API_KEY:
        return _fallback_explanation(outfit_data)

    items = outfit_data.get("items", [])
    items_text = "\n".join(f"- {it['label']}: {it['name']}" for it in items) or "Complete outfit selected"
    stylist_note = outfit_data.get("stylist_rationale", "")
    palette = outfit_data.get("palette") or "not specified"
    price = outfit_data.get("total_price_inr")

    prompt = f"""You are a friendly and knowledgeable AI fashion stylist.

A user said: "{user_message}"

You found this outfit for them:
Theme: {outfit_data.get('theme', '')}
Occasion: {outfit_data.get('occasion', '') or occasion or 'general'}
Gender: {outfit_data.get('gender', '') or gender or 'unisex'}
Color Palette: {palette}
Estimated Price: ₹{price if price is not None else 'N/A'}

Outfit items:
{items_text}

Stylist's original note: {stylist_note}

Write a warm, conversational 3-4 sentence response that:
1. Acknowledges the user's request
2. Introduces the outfit theme
3. Explains WHY these pieces work together (color, occasion, style logic)
4. Gives one practical styling tip

Keep it natural, enthusiastic, and under 120 words."""

    try:
        return _call_gemini(prompt)
    except Exception as e:
        print(f"[llm_service] generate_outfit_explanation fell back: {e}")
        return _fallback_explanation(outfit_data)


def run_conversational_assistant(conversation_history: list, new_message: str) -> str:
    """Multi-turn fashion chat without outfit data (pure conversation, stateless)."""
    if not GEMINI_API_KEY:
        return (
            "I'd love to chat, but my AI brain (Gemini) isn't configured yet. "
            "Ask the developer to set GEMINI_API_KEY in the backend .env file -- "
            "in the meantime, try asking me for an outfit recommendation directly!"
        )

    system_context = (
        "You are a helpful AI fashion stylist assistant. You help users find outfit "
        "recommendations, discuss fashion trends, give styling tips, and answer questions "
        "about clothing, accessories and occasions. Keep responses concise and friendly."
    )

    history_text = ""
    for turn in conversation_history[-6:]:  # last ~3 exchanges
        role = "User" if turn["role"] == "user" else "Assistant"
        history_text += f"{role}: {turn['content']}\n"

    prompt = f"{system_context}\n\nConversation so far:\n{history_text}\nUser: {new_message}\nAssistant:"

    try:
        return _call_gemini(prompt)
    except Exception as e:
        return (
            "I'm having trouble reaching the AI service right now. Please try again in a "
            f"moment. ({e})"
        )


def _fallback_explanation(outfit_data: dict) -> str:
    """Used when Gemini isn't configured or the call fails -- keeps the app fully usable."""
    items = outfit_data.get("items", [])
    hero = next((it["name"] for it in items if it["slot"] == "hero"), "the selected piece")
    footwear = next((it["name"] for it in items if it["slot"] == "footwear"), "matching footwear")
    theme = outfit_data.get("theme") or "this curated look"
    occasion = outfit_data.get("occasion") or "the occasion"
    rationale = outfit_data.get("stylist_rationale", "")

    explanation = f"Here's a great pick for {occasion}: the '{theme}' look. It features {hero} paired with {footwear}."
    if rationale:
        explanation += " " + rationale
    return explanation