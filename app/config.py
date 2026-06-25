"""
Centralised configuration for the Fashion AI backend.

Loads environment variables from a `.env` file (sitting next to this
`app/` package, i.e. the backend project root) and exposes resolved,
typed settings + filesystem paths used across the app.
"""

import os
from dotenv import load_dotenv

# ── Paths ─────────────────────────────────────────────────────────────────
# config.py lives at: <backend_root>/app/config.py
APP_DIR = os.path.dirname(os.path.abspath(__file__))          # .../app (python package)
BACKEND_ROOT = os.path.dirname(APP_DIR)                        # .../<backend_root>

# Load .env from the backend root (where you run `uvicorn app.main:app` from)
load_dotenv(os.path.join(BACKEND_ROOT, ".env"))

DATA_DIR = os.path.join(APP_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
PRODUCTS_PATH = os.path.join(DATA_DIR, "products.csv")
OUTFITS_PATH = os.path.join(DATA_DIR, "outfits.csv")

# ── Gemini / LLM ──────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
# gemini-2.5-flash is stable, free-tier eligible, and supported well past
# this assignment's lifetime. Override via .env if you'd like to try a
# newer model (e.g. gemini-3.5-flash).
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# ── CORS ──────────────────────────────────────────────────────────────────
_default_origins = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174,"
    "http://localhost:3000,http://127.0.0.1:3000"
    "https://fashion-ai-backend-1-rtvk.onrender.com"
)
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()
]

# ── App metadata ──────────────────────────────────────────────────────────
APP_TITLE = "Fashion AI Assistant"
APP_VERSION = "2.1"
