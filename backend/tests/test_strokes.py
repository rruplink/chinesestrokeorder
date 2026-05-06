import pytest

from app.config import Settings
from app.services.strokes import StrokeService


@pytest.mark.asyncio
async def test_common_seed_character_has_stroke_html():
    service = StrokeService(
        Settings(
            metadata_cache_path="backend/tests/.runtime/strokes.sqlite",
            enable_stroke_data_cdn=False,
        )
    )
    html = await service.render_text("你好")
    assert "stroke-svg" in html
    assert await service.missing_chars("你好") == []


@pytest.mark.asyncio
async def test_missing_character_is_reported():
    service = StrokeService(
        Settings(
            metadata_cache_path="backend/tests/.runtime/strokes.sqlite",
            enable_stroke_data_cdn=False,
        )
    )
    assert await service.missing_chars("龘") == ["龘"]
    assert "Stroke data unavailable" in await service.render_text("龘")
