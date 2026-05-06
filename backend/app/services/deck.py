from __future__ import annotations

import html
import tempfile
import zlib
from pathlib import Path

import genanki

from app.models import PreviewCard


CARD_CSS = """
.card {
  font-family: Arial, Helvetica, sans-serif;
  color: #ffffff;
  background: #2b2b2b;
  font-size: 26px;
  line-height: 1.35;
  text-align: center;
}
.front-pinyin {
  display: inline;
  font-size: 30px;
  font-weight: 400;
  margin: 0;
}
.plain-front {
  color: #ffffff;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 30px;
  font-weight: 400;
  line-height: 1.35;
}
.front-definition {
  display: inline;
  color: #ffffff;
  font-size: 30px;
  font-weight: 400;
  margin: 0;
}
.front-definition::before {
  content: " ; ";
}
.front-content {
  padding: 14px 18px;
}
.hanzi {
  font-size: 34px;
  margin: .75rem 0 1rem;
  color: #ffffff;
}
.stroke-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 14px;
}
.stroke-card {
  width: 190px;
  padding: 10px;
  border: 1px solid #555555;
  border-radius: 16px;
  background: #333333;
}
.stroke-card h3 {
  margin: 0 0 8px;
  font-size: 32px;
  color: #ffffff;
}
.stroke-svg {
  width: 170px;
  height: 170px;
}
.stroke-base {
  fill: #111827;
  opacity: .08;
}
.stroke-fill {
  fill: #111827;
  opacity: 0;
  animation: stroke-pop .22s ease-out forwards;
}
.order-line {
  fill: none;
  stroke: #dc2626;
  stroke-width: 36;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 100;
  stroke-dashoffset: 100;
  animation: draw-stroke .7s ease-out forwards;
}
@keyframes draw-stroke {
  to { stroke-dashoffset: 0; }
}
@keyframes stroke-pop {
  to { opacity: .34; }
}
.stroke-placeholder {
  display: grid;
  min-height: 120px;
  place-items: center;
  color: #9a3412;
  border: 1px dashed #f59e0b;
  border-radius: 12px;
  padding: 10px;
}
"""


ANKI_MODEL = genanki.Model(
    2060122401,
    "Basic Hanzi Writing",
    fields=[
        {"name": "Front"},
        {"name": "Back"},
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": """
              <div class="plain-front">{{Front}}</div>
            """,
            "afmt": """
              <div class="plain-front">{{Front}}</div>
              <hr>
              {{Back}}
            """,
        }
    ],
    css=CARD_CSS,
)


def deck_id(deck_name: str) -> int:
    return zlib.crc32(deck_name.encode("utf-8")) or 1


def build_apkg(deck_name: str, cards: list[PreviewCard], stroke_html: list[str]) -> Path:
    deck = genanki.Deck(deck_id(deck_name), deck_name)
    for card, strokes in zip(cards, stroke_html, strict=True):
        front = f"""
          {html.escape(card.pinyin)} ; {html.escape(card.definition)}
        """
        back = f"""
          <div class="hanzi">{html.escape(card.hanzi)}</div>
          <div class="stroke-grid">{strokes}</div>
        """
        note = genanki.Note(
            model=ANKI_MODEL,
            fields=[front, back],
        )
        deck.add_note(note)

    output = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".apkg").name)
    genanki.Package(deck).write_to_file(output)
    return output
