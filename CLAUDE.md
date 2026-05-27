# CLAUDE.md — operating manual for AI coding agents

This file is the canonical context for AI agents (Claude Code, etc.) working on
`doc-extract`. Read this first. Other docs supplement it; this one rules.

## What this project is

A self-hosted REST microservice + minimal web UI for OCR on document images.
The OCR model (**GOT-OCR 2.0**, ~580M params, Apache 2.0) runs locally inside
the backend container — no cloud APIs, no per-page cost.

Two services, one compose stack:

| Service          | Stack                                | Port (internal) |
|------------------|--------------------------------------|-----------------|
| `doc-extract-api`| Python 3.11 + FastAPI + Transformers | 8000            |
| `doc-extract-web`| React 18 + Vite + nginx (alpine)     | 80              |

The web service proxies `/api/*` → `doc-extract-api:8000/*`. This means the
React app calls same-origin `/api/ocr` and **there is no CORS configuration on
the backend**. Do not add CORS middleware; it's intentionally unnecessary.

## The non-negotiable rule: spike first

Before writing service code, validate the model on real target documents.

```python
# scratch/spike.py — one file, ten lines, no framework
from transformers import AutoModel, AutoTokenizer
tok = AutoTokenizer.from_pretrained("stepfun-ai/GOT-OCR2_0", trust_remote_code=True)
m = AutoModel.from_pretrained("stepfun-ai/GOT-OCR2_0", trust_remote_code=True, low_cpu_mem_usage=True).eval()
print(m.chat(tok, "samples/sample1.png", ocr_type="ocr"))
```

If quality is unacceptable, the rest of the architecture is moot — stop and
revisit model choice (see [`docs/DESIGN.md`](docs/DESIGN.md) §3 alternatives).
**Never skip the spike.** Building a FastAPI wrapper around a model that
doesn't work on the user's documents is wasted work.

## Project map

```
doc-extract-api/
├── app/
│   ├── main.py        # FastAPI app, CORS-free, route registration
│   ├── ocr.py         # Model loading (singleton) + inference
│   ├── extract.py     # Field extraction (Phase 2 — POST /extract)
│   └── schemas.py     # Pydantic request/response models
├── tests/             # pytest, hit real model on small sample
├── samples/           # Sample document images (git-LFS or .gitignored)
├── Dockerfile         # python:3.11-slim base, pre-downloads model weights
└── requirements.txt

doc-extract-web/
├── src/
│   ├── App.tsx                    # Top-level state machine: idle | processing | result
│   ├── components/
│   │   ├── FileUpload.tsx         # Drag-and-drop + click-to-browse
│   │   ├── ProgressView.tsx       # Indeterminate spinner + elapsed counter
│   │   └── ResultView.tsx         # Renders extracted text + copy button
│   ├── api.ts                     # fetch() wrapper for /api/ocr
│   └── main.tsx
├── nginx.conf                     # Serves SPA, proxies /api/* → doc-extract-api:8000
└── Dockerfile                     # Multi-stage: node build → nginx alpine
```

## Run / build / test

```bash
docker compose up --build         # full stack at http://localhost:8080
docker compose up doc-extract-api # backend only at http://localhost:8000

# backend dev (faster than rebuilding image)
cd doc-extract-api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend dev (HMR, talks to backend on :8000)
cd doc-extract-web
npm install
npm run dev

# tests
cd doc-extract-api && pytest
```

## Conventions

- **Backend**: Python 3.11, type hints required, Pydantic for I/O models.
  Format with `ruff format`. Lint with `ruff check`.
- **Frontend**: TypeScript strict mode. Plain CSS or CSS Modules (no Tailwind
  yet — keep deps minimal until UI grows). Native `fetch`, no axios.
- **Endpoints**: kebab-case URLs, JSON responses, always include `duration_ms`
  and `model` in OCR responses for observability.
- **Errors**: return JSON `{"error": "<human message>", "code": "<machine slug>"}`
  with the right HTTP status. Don't leak stack traces.

## Things NOT to do

- **Don't add CORS middleware to the backend** — the nginx proxy makes the
  frontend same-origin. Adding CORS only adds an attack surface.
- **Don't lie about progress.** GOT-OCR is one forward pass; intermediate
  progress doesn't exist. Use an indeterminate spinner + elapsed-time counter.
  Don't fabricate a percentage. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §progress.
- **Don't load the model per-request.** Load once at app startup (FastAPI
  lifespan), reuse the singleton. Cold load is ~10–30 s; per-request cost
  would kill throughput.
- **Don't add an async job queue yet.** Synchronous request-response is fine
  for v1 (minutes-per-page is acceptable). Queue only when load demands it.
- **Don't swap the model lightly.** GOT-OCR was chosen for the
  quality/size/license trade-off (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).
  If swapping (e.g., to Qwen2.5-VL for field extraction), document the why.
- **Don't break the two-container split.** Keep `doc-extract-api` reusable
  by other clients; UI must not leak into backend.

## Common pitfalls

- **First container start is slow** (model weights download during build, ~1.5 GB).
  Subsequent starts are fast. Don't "optimize" by downloading at runtime — that
  just moves the slowness to the first request.
- **`trust_remote_code=True` is required** for GOT-OCR; the model ships custom
  modeling code. This is expected, not a security smell for this specific model.
- **GOT-OCR's bundled `modeling_GOT.py` hardcodes `.cuda()` and `.half()`** in
  its `chat()` method. On CPU-only deployments those raise:
  - `AssertionError: Torch not compiled with CUDA enabled`, and
  - `RuntimeError: Input type (c10::Half) and bias type (float) should be the same`
  (the input is cast to fp16 but the model weights stay fp32 because of
  `torch_dtype=torch.float32`).
  `app/ocr.py` patches `torch.Tensor.cuda`, `torch.Tensor.half`,
  `torch.nn.Module.cuda`, and `torch.nn.Module.half` to no-ops at module load
  time *before* `transformers` is imported. **Do not remove the shim** —
  removing it breaks CPU inference. The shim is already guarded by
  `if not torch.cuda.is_available()`, so GPU paths are untouched.
- **`libgl1` and `libglib2.0-0`** are required apt packages for image processing
  on `python:3.11-slim`. Missing these = cryptic import errors at runtime.
- **`client_max_body_size` in nginx defaults to 1 MB**. Set it to ≥25 MB so large
  scans aren't rejected at the proxy before reaching FastAPI.
- **`proxy_read_timeout` in nginx defaults to 60 s**. OCR can run minutes on CPU;
  set the proxy timeout to 300 s+ to match.

## Where to look for what

| Question                                 | File                       |
|------------------------------------------|----------------------------|
| Why GOT-OCR over Tesseract / TrOCR?      | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §model |
| Why two containers, not one?             | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §split |
| Full design rationale, alternatives, UX  | [docs/DESIGN.md](docs/DESIGN.md) |
| How to add an endpoint                   | [CONTRIBUTING.md](CONTRIBUTING.md) §backend |
| How to add a UI component                | [CONTRIBUTING.md](CONTRIBUTING.md) §frontend |
| Dev loop, tests, commit style            | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Open questions (from design doc — not yet decided)

These are real choices the project hasn't made yet. If the user's request
touches one of these, ask before assuming an answer.

- What document types: forms, invoices, IDs, free-form?
- Expected request volume — affects whether to add a queue.
- Single language or multilingual? GOT-OCR is strong on English + Chinese.
- PDF support? Adds `pdf2image` + Poppler; enables real per-page progress.
- Authentication on the REST endpoint? (API key? mTLS? trusted-network only?)
- Result download format — `.txt`, `.json`, or copy-to-clipboard only?
