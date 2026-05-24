from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path

from starlette.background import BackgroundTask
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import MAX_CARDS_PER_DECK, DeckRequest, PreviewCard, PreviewResponse
from app.services.cost import estimate_cost
from app.services.deck import build_apkg
from app.services.metadata import MetadataService
from app.services.parser import normalize_lines, sanitize_filename
from app.services.strokes import StrokeService


app = FastAPI(title="Chinese Stroke Order Anki Deck Generator")

settings = get_settings()
allowed_origins = [
    origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": (
                f"Please enter 1-{MAX_CARDS_PER_DECK} non-empty lines and a deck "
                "name under 120 characters."
            )
        },
    )


@lru_cache
def metadata_service() -> MetadataService:
    return MetadataService(get_settings())


@lru_cache
def stroke_service() -> StrokeService:
    return StrokeService(get_settings())


@app.get("/api/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "deepseekConfigured": "yes" if settings.deepseek_api_key else "no",
        "deepseekModel": settings.deepseek_model,
        "strokeDataCdn": "enabled" if settings.enable_stroke_data_cdn else "disabled",
    }


@app.post("/api/preview", response_model=PreviewResponse)
async def preview(request: DeckRequest) -> PreviewResponse:
    lines = normalize_lines(request.lines)
    _validate_lines(lines)

    cards = await _make_preview_cards(lines[:5])
    ai_count = sum(1 for line in lines if metadata_service().lookup_local(line) is None)
    missing_by_line = await asyncio.gather(
        *(stroke_service().missing_chars(line) for line in lines)
    )
    warnings = _warnings_from_missing(missing_by_line)
    return PreviewResponse(
        deckName=request.deckName.strip(),
        cards=cards,
        cost=estimate_cost(len(lines), ai_count),
        warnings=warnings,
    )


@app.post("/api/generate")
async def generate(request: DeckRequest) -> FileResponse:
    lines = normalize_lines(request.lines)
    _validate_lines(lines)

    cards = await _make_preview_cards(lines)
    strokes = await asyncio.gather(
        *(stroke_service().render_text(card.hanzi) for card in cards)
    )
    apkg = build_apkg(request.deckName.strip(), cards, strokes)
    filename = f"{sanitize_filename(request.deckName)}.apkg"
    return FileResponse(
        apkg,
        media_type="application/octet-stream",
        filename=filename,
        background=BackgroundTask(_unlink_file, apkg),
    )


async def _make_preview_cards(lines: list[str]) -> list[PreviewCard]:
    return await asyncio.gather(*(_make_preview_card(line) for line in lines))


async def _make_preview_card(line: str) -> PreviewCard:
        metadata = await metadata_service().get_metadata(line)
        return PreviewCard(
            hanzi=line,
            pinyin=metadata.pinyin,
            definition=metadata.definition,
            missingStrokeChars=await stroke_service().missing_chars(line),
            needsAiLookup=metadata.needs_ai_lookup,
        )


def _warnings(cards: list[PreviewCard]) -> list[str]:
    missing = sorted({char for card in cards for char in card.missingStrokeChars})
    return _warnings_from_chars(missing)


def _warnings_from_missing(missing_by_line: list[list[str]]) -> list[str]:
    missing = sorted({char for chars in missing_by_line for char in chars})
    return _warnings_from_chars(missing)


def _warnings_from_chars(missing: list[str]) -> list[str]:
    warnings = []
    if missing:
        warnings.append(f"Missing stroke data for: {' '.join(missing)}")
    return warnings


def _validate_lines(lines: list[str]) -> None:
    if not lines:
        raise HTTPException(status_code=400, detail="Enter at least one non-empty line.")
    if len(lines) > MAX_CARDS_PER_DECK:
        raise HTTPException(
            status_code=400,
            detail=f"Decks are limited to {MAX_CARDS_PER_DECK} cards. Split this into smaller decks.",
        )


def _unlink_file(path: Path) -> None:
    path.unlink(missing_ok=True)


static_dir = get_settings().data_dir.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
