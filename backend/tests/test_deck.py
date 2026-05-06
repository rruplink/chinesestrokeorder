import json
import sqlite3
import zipfile
from pathlib import Path

from app.models import PreviewCard
from app.services.deck import build_apkg


def test_build_apkg_creates_file():
    path = build_apkg(
        "Test Deck",
        [
            PreviewCard(
                hanzi="你好",
                pinyin="nǐ hǎo",
                definition="hello",
                missingStrokeChars=[],
                needsAiLookup=False,
            )
        ],
        ["<section>strokes</section>"],
    )
    assert Path(path).exists()
    assert Path(path).suffix == ".apkg"
    assert Path(path).stat().st_size > 0


def test_build_apkg_uses_two_front_back_fields():
    path = build_apkg(
        "Two Field Test",
        [
            PreviewCard(
                hanzi="你好",
                pinyin="nǐ hǎo",
                definition="hello",
                missingStrokeChars=[],
                needsAiLookup=False,
            )
        ],
        ["<section>strokes</section>"],
    )
    with zipfile.ZipFile(path) as archive:
        db_bytes = archive.read("collection.anki2")

    db_path = Path(str(path) + ".anki2")
    db_path.write_bytes(db_bytes)
    conn = sqlite3.connect(db_path)
    try:
        models = json.loads(conn.execute("SELECT models FROM col").fetchone()[0])
        notes = conn.execute("SELECT flds FROM notes").fetchall()
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)

    model = next(iter(models.values()))
    assert model["name"] == "Basic Hanzi Writing"
    assert [field["name"] for field in model["flds"]] == ["Front", "Back"]
    assert len(notes[0][0].split("\x1f")) == 2
