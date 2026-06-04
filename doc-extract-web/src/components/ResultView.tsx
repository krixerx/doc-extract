import { useState } from "react";
import type { OcrResult } from "../api";

interface Props {
  result: OcrResult;
}

export function ResultView({ result }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard not available — fall back silently
    }
  };

  return (
    <div className="result">
      <div className="result__header">
        <div className="result__meta">
          <span className="result__ok">✓ Done</span> in {(result.duration_ms / 1000).toFixed(1)}s ·{" "}
          {result.page_count > 1 ? `${result.page_count} pages · ` : ""}
          {result.model}
        </div>
        <button className="result__copy" onClick={handleCopy} type="button">
          {copied ? "Copied!" : "📋 Copy"}
        </button>
      </div>
      <div className="result__text">{result.text || "(no text extracted)"}</div>
    </div>
  );
}
