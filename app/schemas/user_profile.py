from pydantic import BaseModel
from typing import List, Optional


class UserProfile(BaseModel):
    message: str
    gender: Optional[str] = None
    occasion: Optional[str] = None
    style_preference: Optional[str] = None
    budget_inr: Optional[int] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    gender: Optional[str] = None
    occasion: Optional[str] = None
    style_preference: Optional[str] = None
    budget_inr: Optional[int] = None


class ProductOut(BaseModel):
    id: str
    name: str
    price: Optional[int] = None
    image_url: Optional[str] = None


class RecommendationResponse(BaseModel):
    llm_explanation: str
    outfit: dict


class ChatResponse(BaseModel):
    type: str
    reply: str
    outfit: Optional[dict]