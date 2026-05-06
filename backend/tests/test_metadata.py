import pytest

from app.config import Settings
from app.services.metadata import MetadataService


@pytest.mark.asyncio
async def test_known_dictionary_entry_does_not_need_ai():
    service = MetadataService(
        Settings(metadata_cache_path="backend/tests/.runtime/metadata_known.sqlite")
    )
    result = await service.get_metadata("你好")
    assert result.pinyin == "nǐ hǎo"
    assert "hello" in result.definition
    assert result.needs_ai_lookup is False


@pytest.mark.asyncio
async def test_unknown_entry_falls_back_without_api_key():
    service = MetadataService(
        Settings(metadata_cache_path="backend/tests/.runtime/metadata_unknown.sqlite")
    )
    result = await service.get_metadata("火星猫")
    assert result.pinyin
    assert result.needs_ai_lookup is True
    assert "Definition unavailable" in result.definition
