from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_MODEL")
    metadata_cache_path: Path = Field(
        default=Path("metadata_cache.sqlite"), alias="METADATA_CACHE_PATH"
    )
    data_dir: Path = Path(__file__).resolve().parent / "data"
    stroke_data_cdn_base_url: str = Field(
        default="https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1",
        alias="STROKE_DATA_CDN_BASE_URL",
    )
    enable_stroke_data_cdn: bool = Field(default=True, alias="ENABLE_STROKE_DATA_CDN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
