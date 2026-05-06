import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

type PreviewCard = {
  hanzi: string;
  pinyin: string;
  definition: string;
  missingStrokeChars: string[];
  needsAiLookup: boolean;
};

type PreviewResponse = {
  deckName: string;
  cards: PreviewCard[];
  cost: {
    detectedCards: number;
    aiAssistedCards: number;
    estimatedUsd: number;
    bufferEstimateUsd: string;
    note: string;
  };
  warnings: string[];
};

type HanziWriterData = {
  strokes: string[];
};

const maxCards = 250;

const sample = `你好
中国
我学习中文`;

function linesFromText(text: string): string[] {
  return text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

async function errorMessage(response: Response): Promise<string> {
  const body = await response.text();
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === 'string') return parsed.detail;
    if (Array.isArray(parsed.detail)) return 'Please check your deck input and try again.';
  } catch {
    // Fall through to plain text.
  }
  return body || `Request failed with HTTP ${response.status}.`;
}

function uniqueChineseChars(text: string): string[] {
  const seen = new Set<string>();
  const chars: string[] = [];
  Array.from(text).forEach((char) => {
    if (/[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/u.test(char) && !seen.has(char)) {
      seen.add(char);
      chars.push(char);
    }
  });
  return chars;
}

function StrokePreview({ text }: { text: string }) {
  const [dataByChar, setDataByChar] = useState<Record<string, HanziWriterData | null>>({});
  const chars = uniqueChineseChars(text);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const entries = await Promise.all(chars.map(async (char) => {
        try {
          const response = await fetch(
            `https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${encodeURIComponent(char)}.json`,
          );
          if (!response.ok) return [char, null] as const;
          return [char, await response.json() as HanziWriterData] as const;
        } catch {
          return [char, null] as const;
        }
      }));
      if (!cancelled) setDataByChar(Object.fromEntries(entries));
    }

    if (chars.length > 0) {
      load();
    } else {
      setDataByChar({});
    }

    return () => {
      cancelled = true;
    };
  }, [text]);

  if (chars.length === 0) return null;

  return (
    <div className="stroke-preview-grid">
      {chars.map((char) => {
        const data = dataByChar[char];
        return (
          <div className="mini-stroke" key={char}>
            <strong>{char}</strong>
            {data ? (
              <svg viewBox="0 0 1024 1024" aria-label={`Stroke preview for ${char}`}>
                <rect x="24" y="24" width="976" height="976" rx="24" />
                <g transform="translate(0, 900) scale(1, -1)">
                  {data.strokes.map((stroke, index) => (
                    <path
                      d={stroke}
                      key={stroke}
                      opacity={0.34 + Math.min(index, 8) * 0.06}
                    />
                  ))}
                </g>
              </svg>
            ) : (
              <span className="stroke-loading">loading</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function App() {
  const [deckName, setDeckName] = useState('Chinese Stroke Order');
  const [text, setText] = useState(sample);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  const lines = linesFromText(text);

  async function previewDeck() {
    setBusy(true);
    setStatus('Previewing cards and checking stroke data...');
    setError('');
    try {
      const response = await fetch('/api/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deckName, lines }),
      });
      if (!response.ok) throw new Error(await errorMessage(response));
      setPreview(await response.json());
      setStatus('Preview ready.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed.');
      setStatus('');
    } finally {
      setBusy(false);
    }
  }

  async function generateDeck() {
    setBusy(true);
    setStatus('Generating deck. Fetching stroke data and definitions...');
    setError('');
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deckName, lines }),
      });
      if (!response.ok) throw new Error(await errorMessage(response));
      const blob = await response.blob();
      setStatus('Deck ready. Starting download...');
      const disposition = response.headers.get('content-disposition') ?? '';
      const filename = disposition.match(/filename="?([^"]+)"?/)?.[1] ?? 'Chinese_Stroke_Order.apkg';
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      setStatus('Download started.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Deck generation failed.');
      setStatus('');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <main className="shell">
      <section className="hero">
        <p className="eyebrow">Anki stroke order generator</p>
        <h1>Hanzi Writing Deck Maker</h1>
        <p>
          Paste Chinese words or phrases one per line. Generate Anki cards with pinyin,
          brief definitions, and animated stroke-order backs.
        </p>
      </section>

      <section className="panel">
        <label>
          Deck name
          <input value={deckName} onChange={(event) => setDeckName(event.target.value)} />
        </label>
        <label>
          Chinese input
          <textarea value={text} onChange={(event) => setText(event.target.value)} />
        </label>
        <div className="stats">
          <span>{lines.length} cards detected</span>
          <span>Maximum {maxCards} cards per deck</span>
        </div>
        {lines.length > maxCards && (
          <div className="limit-warning">
            This deck has {lines.length} cards. Split it into chunks of {maxCards} or fewer.
          </div>
        )}
        <div className="actions">
          <button disabled={busy || lines.length === 0 || lines.length > maxCards} onClick={previewDeck}>Preview first 5</button>
          <button disabled={busy || lines.length === 0 || lines.length > maxCards} onClick={generateDeck} className="primary">
            Generate `.apkg`
          </button>
        </div>
        {status && (
          <div className="progress-wrap" aria-live="polite">
            <div className={busy ? 'progress-bar is-active' : 'progress-bar'} />
            <span>{status}</span>
          </div>
        )}
        {error && <pre className="error">{error}</pre>}
      </section>

      {preview && (
        <section className="preview">
          <div className="cost-card">
            <h2>Generation estimate</h2>
            <p>{preview.cost.detectedCards} cards detected</p>
            <p>{preview.cost.aiAssistedCards} may need AI lookup</p>
            <strong>${preview.cost.estimatedUsd.toFixed(4)} dramatic estimate</strong>
            <small>{preview.cost.note}</small>
          </div>

          {preview.warnings.map((warning) => (
            <div className="warning" key={warning}>{warning}</div>
          ))}

          <h2>Preview</h2>
          <div className="cards">
            {preview.cards.map((card) => (
              <article className="card" key={card.hanzi}>
                <div>
                  <span className="tag">Front</span>
                  <h3>{card.pinyin}</h3>
                  <p>{card.definition}</p>
                </div>
                <div>
                  <span className="tag">Back</span>
                  <p className="hanzi">{card.hanzi}</p>
                  {card.missingStrokeChars.length > 0 ? (
                    <p className="missing">Missing strokes: {card.missingStrokeChars.join(' ')}</p>
                  ) : (
                    <p>Stroke data ready</p>
                  )}
                  <StrokePreview text={card.hanzi} />
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
      </main>
      <aside className="placard">built by Seth</aside>
    </>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
