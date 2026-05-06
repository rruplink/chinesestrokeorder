# Chinese Stroke Order Anki Deck Generator

A website for generating downloadable Anki `.apkg` decks from Chinese text.

Each non-empty input line becomes one Anki card:

- Front: pinyin and a brief English definition
- Back: original Chinese text and static stroke-order diagrams

Version 1 is a website download flow only. Browsers cannot reliably save directly
to an arbitrary desktop folder or import into Anki Desktop without a local helper.

## Project Structure

```text
backend/   FastAPI app, Anki deck generation, metadata, stroke rendering
frontend/  React/Vite website
```

## Quick Start

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

The API will run at `http://localhost:8000`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The website will run at `http://localhost:5173`.

## Optional Data

The app ships with a tiny built-in dictionary/stroke seed so it works out of the
box. Missing stroke data is fetched on demand from the Hanzi Writer Data CDN and
cached under `backend/app/data/strokes`.

For production-quality offline coverage:

- Put CC-CEDICT at `backend/app/data/cedict_ts.u8`
- Put Hanzi Writer character JSON files at `backend/app/data/strokes/<char>.json`

The stroke JSON format should match `hanzi-writer-data`, e.g.:

```json
{ "strokes": ["M ... Z", "..."] }
```

## DeepSeek

AI fallback is optional. Set `DEEPSEEK_API_KEY` on the backend server to enable
brief definitions for unknown phrases.

```powershell
$env:DEEPSEEK_API_KEY="..."
```

Without an API key, unknown phrases still receive pinyin and a clear definition
fallback.

## Stroke Order Coverage

Stroke order is not AI-generated. The app uses canonical Hanzi Writer / Make Me
a Hanzi vector data. Browser previews fetch the same data directly from jsDelivr,
and backend deck generation fetches/caches missing character JSON files on demand.

To disable runtime stroke-data fetching:

```powershell
$env:ENABLE_STROKE_DATA_CDN="false"
```

## Tests

```powershell
pip install -r backend/requirements-dev.txt
pytest backend/tests
```
