import { useEffect, useState } from "react";

interface Props {
  filename: string;
  startedAt: number;
}

function formatElapsed(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function ProgressView({ filename, startedAt }: Props) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, []);

  const elapsedMs = now - startedAt;
  const showSlowHint = elapsedMs > 30_000;

  return (
    <div className="progress">
      <div className="progress__filename">✓ {filename} uploaded</div>
      <div className="progress__spinner" role="progressbar" aria-label="Running OCR" />
      <div className="progress__status">Running OCR…</div>
      <div className="progress__elapsed">Elapsed: {formatElapsed(elapsedMs)}</div>
      {showSlowHint && (
        <div className="progress__hint">Large documents can take 1–2 minutes on CPU.</div>
      )}
    </div>
  );
}
