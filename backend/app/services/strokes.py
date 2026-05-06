from __future__ import annotations

import html
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import httpx

from app.config import Settings
from app.services.parser import unique_chinese_chars


class StrokeService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.stroke_dir = settings.data_dir / "strokes"

    async def missing_chars(self, text: str) -> list[str]:
        return [
            char for char in unique_chinese_chars(text) if not await self._load_or_fetch(char)
        ]

    async def render_text(self, text: str) -> str:
        rendered = []
        for char in unique_chinese_chars(text):
            data = await self._load_or_fetch(char)
            if not data:
                rendered.append(self._placeholder(char))
            else:
                rendered.append(self._render_char(char, data["strokes"], data.get("medians")))
        return "\n".join(rendered)

    @lru_cache(maxsize=12000)
    def _load(self, char: str) -> dict | None:
        path = self.stroke_dir / f"{char}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data.get("strokes"), list):
            return None
        return data

    async def _load_or_fetch(self, char: str) -> dict | None:
        local = self._load(char)
        if local or not self.settings.enable_stroke_data_cdn:
            return local
        fetched = await self._fetch(char)
        if fetched:
            self._save(char, fetched)
            self._load.cache_clear()
            return self._load(char)
        return None

    async def _fetch(self, char: str) -> dict | None:
        url = f"{self.settings.stroke_data_cdn_base_url.rstrip('/')}/{quote(char)}.json"
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
                response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict) or not isinstance(data.get("strokes"), list):
            return None
        return data

    def _save(self, char: str, data: dict) -> None:
        self.stroke_dir.mkdir(parents=True, exist_ok=True)
        path = self.stroke_dir / f"{char}.json"
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, separators=(",", ":"))

    def _render_char(self, char: str, strokes: list[str], medians: list | None) -> str:
        escaped_char = html.escape(char)
        base_paths = []
        animated_paths = []
        for index, stroke in enumerate(strokes):
            delay = index * 0.72
            base_paths.append(
                f'<path class="stroke-base" d="{html.escape(stroke, quote=True)}"/>'
            )
            animated_paths.append(
                f'<path class="stroke-fill" d="{html.escape(stroke, quote=True)}" '
                f'style="animation-delay:{delay + 0.45:.2f}s"/>'
            )

        order_lines = self._render_medians(medians) if medians else ""
        return f"""
        <section class="stroke-card">
          <h3>{escaped_char}</h3>
          <svg class="stroke-svg" viewBox="0 0 1024 1024" role="img" aria-label="Stroke order for {escaped_char}">
            <rect x="24" y="24" width="976" height="976" rx="24" fill="#fffaf0" stroke="#d6c6a8" stroke-width="8"/>
            <line x1="512" y1="72" x2="512" y2="952" stroke="#eadcc4" stroke-width="4" stroke-dasharray="18 18"/>
            <line x1="72" y1="512" x2="952" y2="512" stroke="#eadcc4" stroke-width="4" stroke-dasharray="18 18"/>
            <g transform="translate(0, 900) scale(1, -1)">
              {''.join(base_paths)}
              {order_lines}
              {''.join(animated_paths)}
            </g>
          </svg>
          <p>{len(strokes)} strokes</p>
        </section>
        """

    @staticmethod
    def _render_medians(medians: list) -> str:
        lines = []
        for index, median in enumerate(medians):
            if not isinstance(median, list):
                continue
            points = []
            for point in median:
                if (
                    isinstance(point, list)
                    and len(point) == 2
                    and all(isinstance(value, int | float) for value in point)
                ):
                    points.append(f"{point[0]},{point[1]}")
            if len(points) < 2:
                continue
            delay = index * 0.72
            lines.append(
                '<polyline class="order-line" pathLength="100" '
                f'points="{html.escape(" ".join(points), quote=True)}" '
                f'style="animation-delay:{delay:.2f}s"/>'
            )
        return "".join(lines)

    @staticmethod
    def _placeholder(char: str) -> str:
        escaped_char = html.escape(char)
        return f"""
        <section class="stroke-card stroke-missing">
          <h3>{escaped_char}</h3>
          <div class="stroke-placeholder">Stroke data unavailable</div>
        </section>
        """
