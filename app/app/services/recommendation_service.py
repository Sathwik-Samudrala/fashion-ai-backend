"""
Content-based outfit recommendation engine.

Loads the curated products + outfits CSVs once at import time, then:
  1. Extracts gender / occasion / style signals from free-text messages
     (when not explicitly supplied by the client).
  2. Scores every curated outfit against those signals + budget.
  3. Returns the best match (plus the next-best alternatives for
     ranking/explainability) with full product detail (incl. image URLs)
     attached to every slot.
"""

import os
import math
from typing import Optional

import pandas as pd

from app.config import PRODUCTS_PATH, OUTFITS_PATH

# ── Load once at import time ─────────────────────────────────────────────────
try:
    products_df = pd.read_csv(PRODUCTS_PATH, dtype={"id": str})
    outfits_df = pd.read_csv(OUTFITS_PATH, dtype={"outfit_id": str})
except FileNotFoundError as e:
    raise RuntimeError(
        f"Could not load dataset CSVs. Expected files at:\n"
        f"  {PRODUCTS_PATH}\n  {OUTFITS_PATH}\n"
        f"Make sure the data/ folder was included alongside the app. ({e})"
    )

# Normalise string columns used for matching
for col in ["gender", "occasion", "wear_type", "category", "tags", "description"]:
    if col in products_df.columns:
        products_df[col] = products_df[col].fillna("").astype(str).str.lower().str.strip()

for col in ["gender", "occasion", "wear_type", "theme"]:
    if col in outfits_df.columns:
        outfits_df[col] = outfits_df[col].fillna("").astype(str).str.lower().str.strip()

# Index products by id for O(1) lookups
products_df = products_df.set_index("id", drop=False)

# ── Slot metadata (id col -> name col -> human label) ────────────────────────
SLOT_DEFS = [
    ("hero", "hero", "hero_id", "Hero Piece"),
    ("second", "second", "second_id", "Second Piece"),
    ("layer", "layer", "layer_id", "Layer"),
    ("footwear", "footwear", "footwear_id", "Footwear"),
    ("accessory_1", "accessory_1", "accessory_1_id", "Accessory"),
    ("accessory_2", "accessory_2", "accessory_2_id", "Accessory"),
]

# ── Keyword → signal maps ────────────────────────────────────────────────────
OCCASION_KEYWORDS = {
    "office": ["office", "work", "business", "meeting", "professional", "interview", "corporate"],
    "wedding": ["wedding", "bride", "groom", "shaadi", "marriage", "sangeet", "mehendi"],
    "casual": ["casual", "everyday", "weekend", "chill", "relax", "hang out", "street"],
    "sports": ["sports", "gym", "workout", "athletic", "running", "fitness", "exercise"],
    "vacation": ["vacation", "travel", "trip", "beach", "holiday", "outing", "tourist", "summer"],
    "party": ["party", "night out", "club", "cocktail", "date", "dinner", "evening"],
    "festive": ["festive", "festival", "diwali", "eid", "puja", "navratri", "celebration"],
    "winter": ["winter", "cold", "snow", "jacket", "coat", "layering", "chilly"],
}

GENDER_KEYWORDS = {
    "men": ["male", " man", "men", "boy", "guy", "his ", "gents", "gentleman"],
    "women": ["female", "woman", "women", "girl", "lady", "her ", "she ", "ladies"],
}

STYLE_KEYWORDS = {
    "western": ["western", "jeans", "shirt", "tshirt", "t-shirt", "dress", "modern", "contemporary"],
    "ethnic": ["ethnic", "kurta", "saree", "salwar", "sherwani", "traditional", "indian", "kurti"],
}


def _extract_signal(text: str, keyword_map: dict) -> Optional[str]:
    text_lower = f" {text.lower()} "
    for key, keywords in keyword_map.items():
        if any(kw in text_lower for kw in keywords):
            return key
    return None


def _extract_occasion(text: str) -> Optional[str]:
    return _extract_signal(text, OCCASION_KEYWORDS)


def _extract_gender(text: str) -> Optional[str]:
    return _extract_signal(text, GENDER_KEYWORDS)


def _extract_style(text: str) -> Optional[str]:
    return _extract_signal(text, STYLE_KEYWORDS)


# ── Product lookup ────────────────────────────────────────────────────────────

def _to_float(value) -> Optional[float]:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def get_product_details(product_id: Optional[str]) -> Optional[dict]:
    """Look up a product by id. Returns None for missing/blank/NaN ids."""
    if not product_id or (isinstance(product_id, float) and math.isnan(product_id)):
        return None
    product_id = str(product_id).strip()
    if not product_id or product_id.lower() == "nan":
        return None
    if product_id not in products_df.index:
        return None

    r = products_df.loc[product_id]
    image_rel = r.get("image", "") or ""
    return {
        "id": r.get("id", product_id),
        "name": r.get("name", ""),
        "brand": r.get("brand") or None,
        "price_inr": _to_float(r.get("price_inr")),
        "rating": _to_float(r.get("rating")),
        "category": r.get("category", ""),
        "category_label": r.get("category_label", ""),
        "occasion": r.get("occasion", ""),
        "gender": r.get("gender", ""),
        "wear_type": r.get("wear_type", ""),
        "description": r.get("description", ""),
        # Served by StaticFiles mounted at /images -> app/data/images
        "image_url": f"/{image_rel}" if image_rel else None,
        "product_url": r.get("product_url") or None,
    }


def list_products(
    gender: Optional[str] = None,
    occasion: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 60,
) -> list:
    """Filtered product catalog, used by the /api/products browsing endpoint."""
    df = products_df
    if gender:
        df = df[df["gender"] == gender.lower().strip()]
    if occasion:
        df = df[df["occasion"] == occasion.lower().strip()]
    if category:
        df = df[df["category"].str.contains(category.lower().strip(), na=False)]

    out = []
    for _, r in df.head(max(1, min(limit, 200))).iterrows():
        image_rel = r.get("image", "") or ""
        out.append({
            "id": r.get("id"),
            "name": r.get("name", ""),
            "brand": r.get("brand") or None,
            "price_inr": _to_float(r.get("price_inr")),
            "rating": _to_float(r.get("rating")),
            "gender": r.get("gender", ""),
            "occasion": r.get("occasion", ""),
            "category_label": r.get("category_label", ""),
            "image_url": f"/{image_rel}" if image_rel else None,
            "product_url": r.get("product_url") or None,
        })
    return out


# ── Outfit scoring ─────────────────────────────────────────────────────────────

def _score_outfit_row(row, gender: Optional[str], occasion: Optional[str],
                       style: Optional[str], budget: Optional[int]) -> float:
    score = 0.0

    if gender and row.get("gender") == gender:
        score += 3.0
    if occasion and row.get("occasion") == occasion:
        score += 4.0
    if style and row.get("wear_type") == style:
        score += 2.0

    if budget:
        price = _to_float(row.get("total_price_inr"))
        if price is not None:
            if price <= budget:
                score += 1.5
            elif price <= budget * 1.2:
                score += 0.5

    return score


def _build_outfit_items(row) -> list:
    items = []
    for slot, name_col, id_col, label in SLOT_DEFS:
        name = row.get(name_col)
        if not name or (isinstance(name, float) and math.isnan(name)):
            continue  # slot not used in this outfit (e.g. no "layer" piece)

        product = get_product_details(row.get(id_col))
        item = {
            "slot": slot,
            "label": label,
            "name": str(name),
            "product_id": product["id"] if product else None,
            "brand": product["brand"] if product else None,
            "price_inr": product["price_inr"] if product else None,
            "rating": product["rating"] if product else None,
            "image_url": product["image_url"] if product else None,
            "product_url": product["product_url"] if product else None,
        }
        items.append(item)
    return items


def _row_to_outfit_dict(row) -> dict:
    return {
        "outfit_id": row.get("outfit_id"),
        "theme": row.get("theme", ""),
        "occasion": row.get("occasion", ""),
        "gender": row.get("gender", ""),
        "palette": row.get("palette") or None,
        "total_price_inr": _to_float(row.get("total_price_inr")),
        "stylist_rationale": row.get("stylist_rationale", ""),
        "items": _build_outfit_items(row),
    }


def get_outfit_by_id(outfit_id: str) -> Optional[dict]:
    """Fetch one curated outfit by id (used for the 'view alternative' drill-down)."""
    match = outfits_df[outfits_df["outfit_id"].str.lower() == outfit_id.lower().strip()]
    if match.empty:
        return None
    return _row_to_outfit_dict(match.iloc[0])


def find_best_outfit(
    message: str,
    gender: Optional[str] = None,
    occasion: Optional[str] = None,
    style_preference: Optional[str] = None,
    budget_inr: Optional[int] = None,
) -> dict:
    """
    Score every curated outfit against the (explicit or message-extracted)
    user signals, and return the best match along with the next-best
    alternatives for transparency/ranking.
    """
    extracted_gender = gender or _extract_gender(message)
    extracted_occasion = occasion or _extract_occasion(message)
    extracted_style = style_preference or _extract_style(message)

    scored = []
    for _, row in outfits_df.iterrows():
        score = _score_outfit_row(row, extracted_gender, extracted_occasion, extracted_style, budget_inr)
        scored.append((score, row))

    # Highest score first; stable sort keeps CSV order as a deterministic tiebreaker
    scored.sort(key=lambda pair: pair[0], reverse=True)

    if scored[0][0] == 0:
        # Nothing matched any signal at all -> fall back to a random pick
        # so the assistant still has *something* compatible to suggest.
        best_row = outfits_df.sample(1).iloc[0]
        best_score = 0.0
        alt_rows = []
    else:
        best_score, best_row = scored[0]
        alt_rows = scored[1:4]  # next 3 best, for the "alternatives" list

    outfit = _row_to_outfit_dict(best_row)
    outfit["alternatives"] = [
        {
            "outfit_id": r.get("outfit_id"),
            "theme": r.get("theme", ""),
            "score": round(s, 2),
            "total_price_inr": _to_float(r.get("total_price_inr")),
        }
        for s, r in alt_rows
        if s > 0
    ]

    # Internal-only signals, consumed by the route layer to personalise the
    # LLM prompt, then stripped before the response is returned.
    outfit["_extracted_gender"] = extracted_gender
    outfit["_extracted_occasion"] = extracted_occasion
    outfit["_extracted_style"] = extracted_style
    outfit["_match_score"] = round(best_score, 2)

    return outfit