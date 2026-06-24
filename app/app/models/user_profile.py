"""
Pydantic schemas shared across routes and services.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Requests ────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    """Body for POST /api/recommend"""
    message: str = Field(..., min_length=1, description="Natural-language request from the user")
    gender: Optional[str] = Field(None, description='"men" | "women"')
    age: Optional[int] = Field(None, ge=1, le=120)
    occasion: Optional[str] = Field(
        None,
        description="office, wedding, casual, sports, vacation, party, festive, winter",
    )
    style_preference: Optional[str] = Field(None, description='"western" | "ethnic"')
    budget_inr: Optional[int] = Field(None, ge=0)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    """Body for POST /api/chat"""
    messages: List[ChatMessage] = Field(..., min_length=1)
    gender: Optional[str] = None
    occasion: Optional[str] = None
    style_preference: Optional[str] = None
    budget_inr: Optional[int] = Field(None, ge=0)


# ── Responses ────────────────────────────────────────────────────────────────

class OutfitItem(BaseModel):
    """A single piece (hero, footwear, accessory, ...) within a recommended outfit."""
    slot: str                          # hero | second | layer | footwear | accessory_1 | accessory_2
    label: str                         # human-readable label, e.g. "Footwear"
    name: str                          # curated display name, e.g. "Classic Women's Heels (Lavie)"
    product_id: Optional[str] = None
    brand: Optional[str] = None
    price_inr: Optional[float] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None    # relative URL served by the backend, e.g. /images/ajio/123.jpg
    product_url: Optional[str] = None


class OutfitAlternative(BaseModel):
    """A lighter-weight pointer to another compatible outfit, for ranking/explainability."""
    outfit_id: str
    theme: str
    score: float
    total_price_inr: Optional[float] = None


class RecommendationResponse(BaseModel):
    outfit_id: str
    theme: str
    occasion: str
    gender: str
    palette: Optional[str] = None
    total_price_inr: Optional[float] = None
    stylist_rationale: str
    llm_explanation: str
    items: List[OutfitItem]
    alternatives: List[OutfitAlternative] = []


class ChatResponse(BaseModel):
    type: str  # "recommendation" | "conversation"
    reply: str
    outfit: Optional[RecommendationResponse] = None


class ProductOut(BaseModel):
    id: str
    name: str
    brand: Optional[str] = None
    price_inr: Optional[float] = None
    rating: Optional[float] = None
    gender: Optional[str] = None
    occasion: Optional[str] = None
    category_label: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None