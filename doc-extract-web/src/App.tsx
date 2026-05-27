import { useCallback, useRef, useState } from "react";
import "./App.css";
import { OcrApiError, postOcr, type OcrResult } from "./api";
import { FileUpload } from "./components/FileUpload";
import { ProgressView } from "./components/ProgressView";
import { ResultView } from "./components/ResultView";

type State =
  | { kind: "idle" }
  | { kind: "processing"; file: File; startedAt: number }
  | { kind: "result"; result: OcrResult }
  | { kind: "error"; message: string; file?: File };

export function App() {
  const [state, setState] = useState<State>({ kind: "idle" });
  const abortRef = useRef<AbortController | null>(null);

  const handleFile = useCallback(async (file: File) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setState({ kind: "processing", file, startedAt: Date.now() });
    try {
      const result = await postOcr(file, ctrl.signal);
      setState({ kind: "result", result });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const message = e instanceof OcrApiError ? e.message : String(e);
      setState({ kind: "error", message, file });
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState({ kind: "idle" });
  }, []);

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">doc-extract</h1>
        {state.kind !== "idle" && (
          <button className="app__reset" onClick={reset} type="button">
            ↻ New
          </button>
        )}
      </header>

      <main className="app__panel">
        {state.kind === "idle" && <FileUpload onFile={handleFile} />}

        {state.kind === "processing" && (
          <ProgressView filename={state.file.name} startedAt={state.startedAt} />
        )}

        {state.kind === "result" && <ResultView result={state.result} />}

        {state.kind === "error" && (
          <div>
            <div className="result__error">⚠ {state.message}</div>
            {state.file && (
              <button
                className="result__copy"
                style={{ marginTop: 16 }}
                onClick={() => state.file && handleFile(state.file)}
                type="button"
              >
                Retry
              </button>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
