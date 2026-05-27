import { useCallback, useRef, useState } from "react";

interface Props {
  onFile: (file: File) => void;
  accept?: string;
}

const ALLOWED = ["image/png", "image/jpeg", "image/webp", "image/tiff"];
const MAX_BYTES = 25 * 1024 * 1024;

export function FileUpload({ onFile, accept = "image/*" }: Props) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      if (!ALLOWED.includes(file.type)) {
        setError(`Unsupported file type: ${file.type || "unknown"}`);
        return;
      }
      if (file.size > MAX_BYTES) {
        setError(`File too large (max ${MAX_BYTES / 1024 / 1024} MB)`);
        return;
      }
      setError(null);
      onFile(file);
    },
    [onFile],
  );

  return (
    <div
      className={`dropzone ${dragging ? "dropzone--active" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files?.[0];
        if (f) handleFile(f);
      }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
      }}
    >
      <div className="dropzone__icon" aria-hidden>
        📄
      </div>
      <div className="dropzone__primary">Drop image here</div>
      <div className="dropzone__hint">or click to browse</div>
      <div className="dropzone__formats">Supports: PNG, JPG, WEBP, TIFF · up to 25 MB</div>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
          // reset value so selecting the same file twice still fires onChange
          e.target.value = "";
        }}
      />

      {error && <div className="dropzone__error">{error}</div>}
    </div>
  );
}
