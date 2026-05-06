from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import httpx
from pypinyin import Style, lazy_pinyin
from pypinyin.contrib.tone_convert import to_tone

from app.config import Settings


DEFINITION_RE = re.compile(r"/([^/]+)/")


SEED_DICTIONARY: dict[str, tuple[str, str]] = {
    "你": ("nǐ", "you"),
    "好": ("hǎo", "good; well"),
    "你好": ("nǐ hǎo", "hello; hi"),
    "我": ("wǒ", "I; me"),
    "中国": ("Zhōng guó", "China"),
    "中文": ("Zhōng wén", "Chinese language"),
    "谢谢": ("xiè xie", "thanks; thank you"),
    "学习": ("xué xí", "to study; to learn"),
}


@dataclass(frozen=True)
class MetadataResult:
    hanzi: str
    pinyin: str
    definition: str
    source: str
    needs_ai_lookup: bool


class MetadataService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.dictionary = dict(SEED_DICTIONARY)
        self._load_cedict(settings.data_dir / "cedict_ts.u8")
        self._init_cache()

    def lookup_local(self, text: str) -> MetadataResult | None:
        normalized = text.strip()
        if normalized in self.dictionary:
            pinyin, definition = self.dictionary[normalized]
            return MetadataResult(
                normalized, pinyin, self._simple_definition(definition), "dictionary", False
            )
        return None

    async def get_metadata(self, text: str) -> MetadataResult:
        normalized = text.strip()
        local = self.lookup_local(normalized)
        if local:
            return local

        cached = self._cache_get(normalized)
        if cached:
            return MetadataResult(
                normalized,
                cached["pinyin"],
                self._simple_definition(cached["definition"]),
                "cache",
                True,
            )

        pinyin = " ".join(lazy_pinyin(normalized, style=Style.TONE))
        if self.settings.deepseek_api_key:
            try:
                definition = await self._ask_deepseek(normalized, pinyin)
            except httpx.HTTPStatusError as error:
                definition = f"DeepSeek API error: HTTP {error.response.status_code}."
            except httpx.HTTPError:
                definition = "DeepSeek API error: request failed."
            definition = self._simple_definition(definition)
            self._cache_set(normalized, pinyin, definition)
            return MetadataResult(normalized, pinyin, definition, "deepseek", True)

        return MetadataResult(
            normalized,
            pinyin,
            "Definition unavailable.",
            "fallback",
            True,
        )

    def _load_cedict(self, path: Path) -> None:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$", line)
                if not match:
                    continue
                traditional, simplified, numbered_pinyin, raw_defs = match.groups()
                definition = self._brief_definition(raw_defs.split("/"))
                pinyin = self._numbered_to_tone_marks(numbered_pinyin)
                self.dictionary.setdefault(simplified, (pinyin, definition))
                self.dictionary.setdefault(traditional, (pinyin, definition))

    def _init_cache(self) -> None:
        self.settings.metadata_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.settings.metadata_cache_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata_cache (
                    hanzi TEXT PRIMARY KEY,
                    pinyin TEXT NOT NULL,
                    definition TEXT NOT NULL
                )
                """
            )

    def _cache_get(self, text: str) -> dict[str, str] | None:
        with sqlite3.connect(self.settings.metadata_cache_path) as conn:
            row = conn.execute(
                "SELECT pinyin, definition FROM metadata_cache WHERE hanzi = ?",
                (text,),
            ).fetchone()
        if not row:
            return None
        return {"pinyin": row[0], "definition": row[1]}

    def _cache_set(self, text: str, pinyin: str, definition: str) -> None:
        with sqlite3.connect(self.settings.metadata_cache_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO metadata_cache (hanzi, pinyin, definition)
                VALUES (?, ?, ?)
                """,
                (text, pinyin, definition),
            )

    async def _ask_deepseek(self, text: str, pinyin: str) -> str:
        prompt = (
            "Give a very brief learner-friendly English gloss for this Chinese "
            "word or phrase. Use 1 to 4 simple words, no sentence, no examples. "
            "Return JSON only with a string field named definition. "
            f"Chinese: {text}\nPinyin: {pinyin}"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.deepseek_api_key}"},
                json={
                    "model": self.settings.deepseek_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
            definition = str(parsed.get("definition", "")).strip()
        except json.JSONDecodeError:
            definition = content.strip()
        return self._simple_definition(definition) or "Definition unavailable."

    @staticmethod
    def _brief_definition(definitions: list[str]) -> str:
        cleaned = [definition.strip() for definition in definitions if definition.strip()]
        if not cleaned:
            return "Definition unavailable."
        return MetadataService._simple_definition(cleaned[0])

    @staticmethod
    def _simple_definition(definition: str) -> str:
        cleaned = re.sub(r"\([^)]*\)", "", definition).strip()
        cleaned = re.sub(r"\bCL:.*$", "", cleaned).strip()
        for separator in [";", ",", "/", "；", "，"]:
            if separator in cleaned:
                cleaned = cleaned.split(separator, 1)[0].strip()
        cleaned = re.sub(r"^(to be|to)\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[:70] or "Definition unavailable."

    @staticmethod
    def _numbered_to_tone_marks(numbered: str) -> str:
        return " ".join(to_tone(syllable.replace("u:", "v")) for syllable in numbered.split())
