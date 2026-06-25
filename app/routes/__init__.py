from app.config import GEMINI_API_KEY

from app.schemas.user_profile import (
    ChatRequest,
    ChatResponse,
    ProductOut,
    RecommendationResponse,
    UserProfile,
)

from app.services.llm_service import (
    generate_outfit_explanation,
    run_conversational_assistant,
)

from app.services.recommendation_service import (
    find_best_outfit,
    get_outfit_by_id,
    list_products,
    outfits_df,
    products_df,
)