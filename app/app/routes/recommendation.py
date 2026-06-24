from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import GEMINI_API_KEY
from app.models.user_profile import (
    ChatRequest,
    ChatResponse,
    ProductOut,
    RecommendationResponse,
    UserProfile,
)
from app.services.llm_service import generate_outfit_explanation, run_conversational_assistant
from app.services.recommendation_service import (
    find_best_outfit,
    get_outfit_by_id,
    list_products,
    outfits_df,
    products_df,
)

router = APIRouter()


def _finalize_outfit(outfit: dict, user_message: str) -> dict:
    """Pop internal signals, attach the LLM explanation, return a response-ready dict."""
    extracted_gender = outfit.pop("_extracted_gender", None)
    extracted_occasion = outfit.pop("_extracted_occasion", None)
    outfit.pop("_extracted_style", None)
    outfit.pop("_match_score", None)

    try:
        llm_explanation = generate_outfit_explanation(
            user_message=user_message,
            outfit_data=outfit,
            gender=extracted_gender,
            occasion=extracted_occasion,
        )
    except Exception:
        llm_explanation = outfit.get("stylist_rationale", "Great outfit choice!")

    outfit["llm_explanation"] = llm_explanation
    return outfit


@router.post("/recommend", response_model=RecommendationResponse)
def recommend_outfit(profile: UserProfile):
    """
    Main recommendation endpoint.
    Accepts a natural-language message plus optional structured user profile fields.
    Returns a complete outfit (with resolved product images) and an LLM-generated explanation.
    """
    try:
        outfit = find_best_outfit(
            message=profile.message,
            gender=profile.gender,
            occasion=profile.occasion,
            style_preference=profile.style_preference,
            budget_inr=profile.budget_inr,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation engine error: {e}")

    return _finalize_outfit(outfit, profile.message)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Multi-turn conversational fashion assistant.
    If the latest message clearly asks for an outfit recommendation, the
    recommendation engine is also invoked and the outfit is attached to the reply.
    """
    latest = request.messages[-1].content
    history = [{"role": m.role, "content": m.content} for m in request.messages[:-1]]

    OUTFIT_TRIGGERS = [
        "recommend", "suggest", "outfit", "wear", "dress", "look",
        "style", "need something", "what should i", "help me find",
        "give me", "show me",
    ]
    is_recommendation_request = any(t in latest.lower() for t in OUTFIT_TRIGGERS)

    if is_recommendation_request:
        try:
            outfit = find_best_outfit(
                message=latest,
                gender=request.gender,
                occasion=request.occasion,
                style_preference=request.style_preference,
                budget_inr=request.budget_inr,
            )
            outfit = _finalize_outfit(outfit, latest)
            return {
                "type": "recommendation",
                "reply": outfit["llm_explanation"],
                "outfit": outfit,
            }
        except Exception as e:
            # Fall through to a plain conversational reply rather than a 500 --
            # the user typed something that *looked* like a recommendation
            # request but the engine choked; don't leave them stuck.
            print(f"[routes.chat] recommendation path failed, falling back to chat: {e}")

    reply = run_conversational_assistant(history, latest)
    return {"type": "conversation", "reply": reply, "outfit": None}


@router.get("/outfits/{outfit_id}", response_model=RecommendationResponse)
def get_outfit(outfit_id: str):
    """Fetch one specific curated outfit by id (used to drill into an 'alternative')."""
    outfit = get_outfit_by_id(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail=f"No outfit found with id '{outfit_id}'")
    outfit["alternatives"] = []
    return _finalize_outfit(outfit, "Tell me about this outfit.")


@router.get("/products", response_model=list[ProductOut])
def get_products(
    gender: Optional[str] = Query(None, description='"men" | "women"'),
    occasion: Optional[str] = None,
    category: Optional[str] = Query(None, description="Substring match, e.g. 'shirt'"),
    limit: int = Query(60, ge=1, le=200),
):
    """Browse the underlying product catalog (dataset analysis / demo support)."""
    return list_products(gender=gender, occasion=occasion, category=category, limit=limit)


@router.get("/occasions")
def get_occasions():
    return {"occasions": ["office", "wedding", "casual", "sports", "vacation", "party", "festive", "winter"]}


@router.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": bool(GEMINI_API_KEY),
        "products_loaded": int(len(products_df)),
        "outfits_loaded": int(len(outfits_df)),
    }