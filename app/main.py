import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import APP_TITLE, APP_VERSION, CORS_ORIGINS, IMAGES_DIR
from app.routes.recommendation import router as recommendation_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fashion-ai")

app = FastAPI(
    title=APP_TITLE,
    description="AI-powered Outfit Recommendation System using Gemini + curated fashion dataset",
    version=APP_VERSION,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Explicit dev-server origins from config, plus a regex fallback so any
# localhost port works out of the box during development/demos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://fashion-ai-frontend-osvx.onrender.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static product images ────────────────────────────────────────────────────
# products.csv / outfits.csv reference paths like "images/ajio/123.jpg";
# mounting here at /images means a product's `image_url` (e.g. "/images/ajio/123.jpg")
# resolves directly against this backend's origin.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

app.include_router(recommendation_router, prefix="/api")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check the backend logs for details."},
    )


@app.get("/")
def home():
    return {"message": "Fashion AI Backend Running", "version": APP_VERSION, "docs": "/docs"}
