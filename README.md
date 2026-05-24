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

## Deploying Under an Existing Domain

The easiest production shape is to run this app as a separate service and route
part of your existing website to it. For example:

```text
https://yourdomain.com/tools/anki-stroke-order
```

Build the frontend with the public path and API path that users will see:

```powershell
cd frontend
$env:VITE_BASE_PATH="/tools/anki-stroke-order/"
$env:VITE_API_BASE_URL="/tools/anki-stroke-order"
npm run build
```

The Dockerfile already builds the frontend and copies it into the FastAPI app.
For container deployments, pass the same values as build args:

```powershell
docker build `
  --build-arg VITE_BASE_PATH="/tools/anki-stroke-order/" `
  --build-arg VITE_API_BASE_URL="/tools/anki-stroke-order" `
  -t anki-stroke-order-generator .
```

Configure your existing website, reverse proxy, or platform router so requests
under `/tools/anki-stroke-order` are forwarded to this app. The cleanest setup is
to strip the prefix before forwarding:

```text
/tools/anki-stroke-order/*  ->  http://anki-generator-service:8000/*
```

With that routing, the frontend loads its assets from
`/tools/anki-stroke-order/` and calls:

```text
/tools/anki-stroke-order/api/preview
/tools/anki-stroke-order/api/generate
```

Those requests reach the FastAPI backend as `/api/preview` and `/api/generate`
after the proxy removes the `/tools/anki-stroke-order` prefix.

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
