# doc-extract — Design Document

> A self-hosted microservice that extracts text (and structured fields) from document images using a local AI OCR model.

**Status:** Draft
**Owner:** erkikriks@gmail.com
**Date:** 2026-05-27

---

## 1. Goal

A self-hosted REST microservice that accepts an uploaded document image (scan, photo, PDF page) and returns extracted text. The service must:

- Run a **tiny AI OCR model locally** (no cloud API calls, no per-page cost).
- Be **dockerized** so it deploys as an independent microservice.
- Tolerate slow inference (seconds to minutes per page is acceptable).
- Optionally extract **specific fields** (e.g. `first_name`, `last_name`) — not just raw text.

---

## 2. Architecture

```
┌──────────────┐       ┌─────────────────────────┐       ┌───────────────────────────┐
│   Browser    │ ────▶ │   doc-extract-web (Docker)      │ ────▶ │   doc-extract-api (Docker)        │
│              │       │                         │       │                           │
│  React UI    │ ◀──── │   React + Vite          │ ◀──── │   FastAPI (Python)        │
│              │       │   served by nginx       │       │         │                 │
└──────────────┘       │   :80                   │       │         ▼                 │
                       │                         │       │   GOT-OCR 2.0 model       │
                       │   (proxies /api → doc-extract-api)      │   (HuggingFace, local)    │
                       └─────────────────────────┘       └───────────────────────────┘
                                                                    :8000
                              ─── docker-compose network ────
```

**Two containers, one stack** (orchestrated via `docker-compose`):
- `doc-extract-api` — FastAPI + model. Pure REST microservice; reusable by any client.
- `doc-extract-web` — React SPA built with Vite, served by nginx, proxies `/api/*` to `doc-extract-api`.

Keeping them separate means the API stays a clean microservice (other services can call it without the UI in the way), while the UI gets its own deploy cadence and scaling profile.

---

## 3. Technology Choices

### Backend (doc-extract-api)

| Layer        | Choice                          | Why                                                                 |
|--------------|---------------------------------|---------------------------------------------------------------------|
| Language     | Python 3.11                     | Native ecosystem for HuggingFace Transformers.                      |
| Web framework| FastAPI + Uvicorn               | Async, OpenAPI docs out-of-the-box, minimal boilerplate.            |
| OCR model    | **GOT-OCR 2.0** (~580M params)  | Purpose-built for document OCR; runs on CPU; high quality on scans. |
| ML runtime   | PyTorch (CPU) + Transformers    | Standard, well-supported.                                           |
| Container    | Docker (python:3.11-slim base)  | Standard microservice deployment.                                   |

### Frontend (doc-extract-web)

| Layer        | Choice                          | Why                                                                 |
|--------------|---------------------------------|---------------------------------------------------------------------|
| Framework    | React 18                        | Most familiar SPA framework; large ecosystem.                        |
| Build tool   | Vite                            | Fast dev server, small production bundles, zero-config TypeScript.   |
| HTTP client  | Native `fetch` API              | No extra dependency needed for this scope.                           |
| Styling      | Plain CSS / CSS Modules         | Keep it simple; can swap for Tailwind later if UI grows.             |
| Web server   | nginx (alpine)                  | Tiny image, serves static build + proxies `/api/*` to backend.       |
| Container    | Multi-stage Docker build        | Node for build, nginx for runtime — final image ~30MB.               |

### Why GOT-OCR 2.0?

- **Purpose-built for document OCR** — handles tables, formulas, multi-column layouts.
- **~580M parameters** — fits in <2GB RAM, runs on CPU.
- **One-shot** — no separate detection + recognition steps (unlike TrOCR).
- **Apache 2.0 licensed** — safe for commercial use.
- **Trade-off:** larger than minimal alternatives (Florence-2 at 230M, TrOCR-small at 60M), but quality on real scans is significantly better.

### Alternatives considered

| Model            | Size    | Verdict                                                       |
|------------------|---------|---------------------------------------------------------------|
| Tesseract        | ~30MB   | Not AI; OK for clean text, poor on real-world scans.          |
| TrOCR-small      | 60M     | Needs separate text-detection step → more plumbing.            |
| Florence-2-base  | 230M    | Smaller but weaker on complex layouts.                         |
| **GOT-OCR 2.0**  | **580M**| **Sweet spot for quality/size on documents.**                  |
| Qwen2.5-VL-3B    | 3B      | Larger; useful if we need direct field extraction (see §6).    |

---

## 4. REST API

### `POST /ocr`

Extract raw text from an uploaded image.

**Request:**
```http
POST /ocr
Content-Type: multipart/form-data

file: <binary image data>
```

**Response (200):**
```json
{
  "text": "Full extracted text from the document...",
  "duration_ms": 4521,
  "model": "GOT-OCR-2.0"
}
```

**Errors:**
- `400` — invalid file type or no file
- `413` — file too large
- `500` — model inference failure

---

### `POST /extract` (Phase 2 — see §6)

Extract specific named fields from an image.

**Request:**
```http
POST /extract
Content-Type: multipart/form-data

file: <binary image data>
fields: ["first_name", "last_name", "date_of_birth"]
```

**Response (200):**
```json
{
  "fields": {
    "first_name": "Erki",
    "last_name": "Kriks",
    "date_of_birth": "1990-03-15"
  },
  "raw_text": "...",
  "duration_ms": 5102
}
```

---

### `GET /health`

Liveness/readiness probe. Returns `200 OK` once the model is loaded.

---

## 5. Project Structure

```
doc-extract/
├── doc-extract-api/                     # Backend service
│   ├── app/
│   │   ├── main.py              # FastAPI app, routes, CORS config
│   │   ├── ocr.py               # Model loading + inference
│   │   ├── extract.py           # Field extraction (Phase 2)
│   │   └── schemas.py           # Pydantic request/response models
│   ├── tests/
│   │   └── test_ocr.py
│   ├── samples/                 # Sample document images for testing
│   ├── Dockerfile
│   └── requirements.txt
│
├── doc-extract-web/                     # Frontend service
│   ├── src/
│   │   ├── App.tsx              # Top-level component
│   │   ├── components/
│   │   │   ├── FileUpload.tsx   # Drag-and-drop / file picker
│   │   │   ├── ProgressView.tsx # Spinner + status messages
│   │   │   └── ResultView.tsx   # Renders extracted text
│   │   ├── api.ts               # fetch() wrapper for /api/ocr
│   │   └── main.tsx
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── nginx.conf               # Proxies /api/* → doc-extract-api:8000
│   └── Dockerfile               # Multi-stage: node build → nginx
│
├── docker-compose.yml           # Orchestrates both services
└── README.md
```

---

## 6. Field Extraction Strategy (Phase 2)

`POST /ocr` gives you raw text. Getting `first_name` and `last_name` out of that text is a separate problem with three viable approaches:

### Option A: Regex / template matching
- Best when documents have a **fixed layout** (e.g. always "Name: <value>" on line 3).
- Zero extra dependencies.
- Brittle if document layouts vary.

### Option B: Rule-based + small NLP library
- spaCy or similar for named-entity recognition.
- Adds ~500MB to the image.
- Works on free-form text but accuracy varies.

### Option C: Swap to a vision-language model (Qwen2.5-VL-3B)
- Prompt directly: *"Extract first_name and last_name from this document as JSON"*
- **Single step** — no separate parsing layer.
- Model is ~5× bigger than GOT-OCR (3B vs 580M params).
- Higher accuracy on varied document layouts.

**Recommendation:** Start with Option A for known document types. If field accuracy is poor across varied inputs, evaluate Option C as a separate `/extract` endpoint (keep `/ocr` on GOT-OCR for pure text extraction).

---

## 7. Frontend UX Flow

A minimal single-page UI. Three states, one screen.

### State 1 — Idle (initial load)

```
┌─────────────────────────────────────────────────┐
│                  doc-extract                    │
│                                                 │
│        ┌─────────────────────────────┐          │
│        │                             │          │
│        │   📄  Drop image here       │          │
│        │       or click to browse    │          │
│        │                             │          │
│        └─────────────────────────────┘          │
│                                                 │
│        Supports: PNG, JPG, PDF                  │
└─────────────────────────────────────────────────┘
```

### State 2 — Processing (after upload)

```
┌─────────────────────────────────────────────────┐
│                  doc-extract                    │
│                                                 │
│        ┌─────────────────────────────┐          │
│        │   ✓ document.png uploaded   │          │
│        └─────────────────────────────┘          │
│                                                 │
│        ⟳  Running OCR — this may take a         │
│            minute on CPU…                       │
│                                                 │
│        Elapsed: 0:23                            │
└─────────────────────────────────────────────────┘
```

### State 3 — Result

```
┌─────────────────────────────────────────────────┐
│                  doc-extract             [↻ new]│
│                                                 │
│   ✓ Done in 31s                                 │
│                                                 │
│   ┌─────────────────────────────────────────┐   │
│   │ Extracted text:                         │   │
│   │                                         │   │
│   │ Lorem ipsum dolor sit amet, consec-     │   │
│   │ tetur adipiscing elit. Sed do eius-     │   │
│   │ mod tempor incididunt ut labore...      │   │
│   │                                         │   │
│   │                              [📋 Copy]  │   │
│   └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Progress reporting — important note

GOT-OCR inference is a single forward pass; it does **not** expose intermediate progress. So "real" progress bars aren't possible without lying. The honest UX is:

- Show an **indeterminate spinner** + an **elapsed-time counter** so the user knows the app is alive.
- Show a friendly hint after 30s: *"Large documents can take 1–2 minutes on CPU."*

If we later want true progress (per-page in a multi-page PDF, for example), we'd switch the backend to **Server-Sent Events** (`POST /ocr/stream`) that emit events like `{"page": 2, "of": 5}`. Not needed for v1.

### Error states (also handled)

- Upload rejected (wrong file type / too large) → inline error on the upload zone.
- API unreachable → banner with retry button.
- OCR inference error → show error message, keep the uploaded file so user can retry.

---

## 8. Dockerization

### Backend Dockerfile sketch (`doc-extract-api/Dockerfile`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for PyTorch + image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download model weights at build time (avoids slow first request)
RUN python -c "from transformers import AutoModel, AutoTokenizer; \
    AutoModel.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True); \
    AutoTokenizer.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True)"

COPY app/ ./app/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile sketch (`doc-extract-web/Dockerfile`)

Multi-stage build — Node for compilation, nginx for runtime.

```dockerfile
# Stage 1 — build the React app
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2 — serve static files + proxy /api
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### nginx config sketch (`doc-extract-web/nginx.conf`)

```nginx
server {
  listen 80;

  # Serve the React SPA
  location / {
    root /usr/share/nginx/html;
    try_files $uri /index.html;
  }

  # Proxy API calls to the backend container
  location /api/ {
    proxy_pass http://doc-extract-api:8000/;
    proxy_set_header Host $host;
    client_max_body_size 25M;          # allow large document uploads
    proxy_read_timeout 300s;           # OCR may take minutes
  }
}
```

This setup means the React app calls `/api/ocr` (same origin) — **no CORS configuration needed** in the backend.

### `docker-compose.yml` sketch

```yaml
services:
  doc-extract-api:
    build: ./doc-extract-api
    # no port exposed to host — only reachable via doc-extract-web
    restart: unless-stopped

  doc-extract-web:
    build: ./doc-extract-web
    ports:
      - "8080:80"      # browse to http://localhost:8080
    depends_on:
      - doc-extract-api
    restart: unless-stopped
```

Bring up the whole stack with `docker compose up`.

### Image size considerations

| Image      | Size    |
|------------|---------|
| doc-extract-api    | ~2.5GB (Python + PyTorch CPU + 1.5GB model weights) |
| doc-extract-web    | ~30MB  (nginx:alpine + React static build)          |

**Optimization options if backend size matters:**
- Mount model weights as a volume instead of baking in (image shrinks to ~1GB, but first start downloads model).
- Use `pytorch/pytorch:2.x-cpu-slim` base instead of building from `python:3.11-slim`.

---

## 9. Performance Expectations

| Hardware                    | Per-page latency (estimate) |
|-----------------------------|-----------------------------|
| Laptop CPU (8 cores)        | 10–30 seconds               |
| Server CPU (16+ cores)      | 5–15 seconds                |
| GPU (any modern CUDA card)  | <1 second                   |

User has stated minutes-per-page is acceptable, so CPU-only is fine for now.

---

## 10. Development Plan

1. **Spike** — 10-line Python script that loads GOT-OCR and OCRs one sample image. Validate quality on real target documents *before* writing any service code.
2. **Backend service** — wrap the spike in FastAPI; one `POST /ocr` endpoint + `GET /health`.
3. **Backend container** — write `doc-extract-api/Dockerfile`, verify it runs standalone.
4. **Frontend skeleton** — `npm create vite@latest` (React + TypeScript), build the three UI states (idle / processing / result) against a mocked API response first.
5. **Frontend container** — write `doc-extract-web/Dockerfile` + `nginx.conf`.
6. **Compose** — write `docker-compose.yml`, wire it all up, end-to-end test in a browser.
7. **Field extraction** — add `POST /extract` (backend) + a fields-selector UI on the result screen (frontend).
8. **Iterate** — if regex isn't enough for varied documents, evaluate Qwen2.5-VL swap.

---

## 11. Open Questions

- [ ] What document types will this primarily handle? (forms, invoices, IDs, free-form letters?)
- [ ] Expected request volume? (1/hour vs 100/hour changes hosting decisions)
- [ ] Will documents always be in one language, or multilingual? (GOT-OCR handles English + Chinese well; other languages may need different model)
- [ ] PDF support needed, or images only? (PDF support = extra dependency: `pdf2image` + Poppler; also enables real per-page progress reporting in the UI)
- [ ] Authentication on the REST endpoint? (API key header? mTLS? open inside a trusted network?)
- [ ] Should the frontend allow downloading the result as `.txt` / `.json`, or copy-to-clipboard only?
- [ ] Branding for the UI — logo, color scheme, display name? (Currently using the project name `doc-extract` as the title; may want a friendlier display name like "Document Extractor".)

---

## 12. Future Considerations

- **Batch endpoint** for processing multiple images in one request.
- **Real progress reporting** via Server-Sent Events (`POST /ocr/stream`) — only meaningful once PDF/multi-page support exists.
- **Async job queue** (Redis + worker) if requests pile up under load — frontend would then poll a job ID instead of holding the upload connection open.
- **GPU support** via a separate Dockerfile variant if latency becomes critical.
- **Camunda integration** — could be invoked as an external task or REST connector from a BPMN process (relevant given the rest-datasonnet-connector work).
- **History view** in the frontend — persist past OCR results locally (IndexedDB) so users can revisit previous documents.
