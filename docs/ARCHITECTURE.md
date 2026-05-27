# Architecture

This document captures the *why* behind doc-extract's structure. The *what*
lives in [../README.md](../README.md); the *how to develop* lives in
[../CONTRIBUTING.md](../CONTRIBUTING.md); the full design exploration and
rejected alternatives live in [DESIGN.md](DESIGN.md).

## System diagram

```
┌──────────┐      ┌────────────────────┐      ┌──────────────────────┐
│ Browser  │ ───▶ │ doc-extract-web    │ ───▶ │ doc-extract-api      │
│          │      │ (nginx :80)        │      │ (FastAPI :8000)      │
│ React UI │ ◀─── │ React SPA + proxy  │ ◀─── │ GOT-OCR 2.0 (local)  │
└──────────┘      └────────────────────┘      └──────────────────────┘
                          └──────── docker compose network ───────┘
```

## Why two containers, not one  <a id="split"></a>

The API is a **reusable microservice**. Any client — a CLI, another service,
a BPMN process step, a future mobile app — can call `POST /ocr` directly. The
UI is one consumer among many.

Bundling them in one container would:
- Force every API consumer to ship the React build with them, or
- Force the API to grow a UI route layer it doesn't otherwise need, and
- Couple the deploy cadence of two things that change at very different rates.

Two containers means each side has its own dependency tree, its own image
size, and its own scaling profile (the API is the expensive one).

## Why nginx proxies `/api/*` instead of CORS

The frontend calls `/api/ocr` — same origin as the SPA itself, because nginx
proxies `/api/*` to the backend. This avoids CORS entirely.

Browser-side CORS configuration is a recurring source of footguns
(preflight failures, credentialed-request edge cases, dev-vs-prod drift). By
making API calls same-origin via a reverse proxy, the backend never has to
think about origins, and the frontend just calls relative URLs. The cost is
one `proxy_pass` block in nginx config — a worthwhile trade.

## Why GOT-OCR 2.0  <a id="model"></a>

The model choice is the single most consequential decision in the stack. The
shortlist and verdicts:

| Model            | Size  | Verdict                                                   |
|------------------|-------|-----------------------------------------------------------|
| Tesseract        | 30 MB | Not AI; clean text only, poor on real scans               |
| TrOCR-small      | 60 M  | Needs separate text-detection step — more plumbing        |
| Florence-2-base  | 230 M | Smaller but weaker on multi-column / complex layouts      |
| **GOT-OCR 2.0**  | **580 M** | **Sweet spot for quality vs. size on documents**      |
| Qwen2.5-VL-3B    | 3 B   | Larger; useful when direct field extraction is needed     |

GOT-OCR wins on four axes for *this* problem:

1. **Purpose-built for document OCR** — tables, formulas, multi-column work
   without manual layout analysis.
2. **One-shot** — no separate detect-then-recognize pipeline like TrOCR.
3. **Fits in <2 GB RAM, runs on CPU** — the deployment constraint.
4. **Apache 2.0 license** — safe for commercial use, safe to share.

The 580M parameter count is the cost of admission for the quality. Smaller
models (TrOCR, Florence-2) save image size but pay for it in worse output on
real-world scans. The user has accepted minutes-per-page latency, which makes
CPU inference viable — so the model size is a one-time image-size hit, not a
recurring runtime cost.

## Why pre-download model weights at build time

The API Dockerfile runs `AutoModel.from_pretrained(...)` during build. This
bakes the ~1.5 GB of model weights into the image.

Alternatives considered:
- **Download on first request** — moves a 30–60 s download into the first
  user's request. Bad UX, hard to debug.
- **Mount weights as a volume** — image shrinks to ~1 GB, but the operator
  has to manage the volume's contents. Reasonable for production; over-engineered
  for v1.

Baking weights in trades image size for startup speed and operational
simplicity. The image is large (~2.5 GB) but the container is *ready* the
moment it starts. For a service where the model *is* the product, this is
the right trade.

## Why an indeterminate spinner instead of a progress bar  <a id="progress"></a>

GOT-OCR runs as a single forward pass. The model does not expose intermediate
progress, and the network/server can't fake one without lying.

The honest UI is:
- An **indeterminate spinner** (it's working, we don't know how much longer).
- An **elapsed-time counter** (proof the app is alive).
- A **friendly hint after 30 s** ("Large documents can take 1–2 minutes on CPU").

The alternative — a progress bar that ticks up on a guessed schedule — looks
nicer for the first ten seconds and erodes trust thereafter. We don't lie to
users.

Real per-page progress becomes available only when multi-page PDFs land. At
that point a streaming endpoint (`POST /ocr/stream` over Server-Sent Events,
emitting `{"page": 2, "of": 5}`) becomes meaningful.

## Why no async job queue (yet)

Synchronous request-response works because the user has accepted
minutes-per-page latency. The browser holds the upload connection open;
nginx's `proxy_read_timeout` is widened to 300 s; FastAPI processes one
request at a time per worker.

A Redis + worker queue is the right answer once any of the following is true:
- Concurrent request volume exceeds what a single worker can serve.
- Requests need to survive a backend restart.
- The frontend wants to disconnect and poll for results later.

None of these are true for v1. Adding the queue now adds operational
complexity (Redis, workers, job state) for zero current benefit.

## Field extraction is a separate phase

`POST /ocr` returns raw text. Turning that text into named fields
(`first_name`, `last_name`, etc.) is a distinct problem with three viable
solutions (regex, NLP library, vision-language model). See
[DESIGN.md](DESIGN.md) §6 for the full trade-off analysis.

The phased approach — ship `/ocr` first, add `/extract` later when the field
strategy is chosen — keeps v1 small and unblocks the harder problem from the
easier one.

## Layered roadmap

1. **Spike**: validate GOT-OCR on real target documents *before* writing
   service code. See [../CLAUDE.md](../CLAUDE.md) "spike first".
2. **Backend service**: FastAPI + `POST /ocr` + `GET /health`. One container.
3. **Frontend**: React SPA with idle / processing / result states, mocked
   API first.
4. **Compose**: wire the two together end-to-end.
5. **Field extraction**: `POST /extract` + UI fields selector.
6. **Iterate**: revisit model choice if regex isn't enough for varied inputs.

Each layer is independently shippable and verifies a key assumption.
