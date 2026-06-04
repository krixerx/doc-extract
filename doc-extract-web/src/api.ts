export interface OcrResult {
  text: string;
  pages: string[];
  page_count: number;
  duration_ms: number;
  model: string;
}

export interface ApiError {
  error: string;
  code: string;
}

export class OcrApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/** POST a file to the OCR endpoint. Throws OcrApiError on non-2xx. */
export async function postOcr(file: File, signal?: AbortSignal): Promise<OcrResult> {
  const form = new FormData();
  form.append("file", file);

  let res: Response;
  try {
    res = await fetch("/api/ocr", { method: "POST", body: form, signal });
  } catch (e) {
    throw new OcrApiError(0, "network_error", e instanceof Error ? e.message : "Network error");
  }

  if (!res.ok) {
    let payload: ApiError | undefined;
    try {
      const body = await res.json();
      payload = body?.detail ?? body;
    } catch {
      // ignore JSON parse errors
    }
    throw new OcrApiError(
      res.status,
      payload?.code ?? "http_error",
      payload?.error ?? `HTTP ${res.status}`,
    );
  }

  return (await res.json()) as OcrResult;
}
