# Contributing

How to develop on doc-extract locally. For project context, start with
[README.md](README.md) and [CLAUDE.md](CLAUDE.md).

## Prerequisites

- Docker + Docker Compose (for the full stack)
- Python 3.11 + pip (for backend dev)
- Node.js 20+ + npm (for frontend dev)

## Local dev loop

The fastest loop is to run each service natively (not through Docker), so
HMR and hot reload work.

```bash
# terminal 1 — backend
cd doc-extract-api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend
cd doc-extract-web
npm install
npm run dev      # vite dev server on :5173, proxies /api → :8000
```

Vite's `server.proxy` config forwards `/api/*` to `http://localhost:8000`
during dev, mirroring what nginx does in production. The frontend code is
identical in both modes.

For a closer-to-production check before shipping:

```bash
docker compose up --build
```

## Adding a backend endpoint  <a id="backend"></a>

1. Define request/response shapes in `app/schemas.py` (Pydantic models).
2. Add the handler to `app/main.py` (or a new module imported by `main.py`).
3. Reuse the model singleton from `app/ocr.py`; don't load the model again.
4. Always include `duration_ms` and `model` in OCR-flavored responses for
   observability and parity with existing endpoints.
5. Add a test in `tests/` that hits the endpoint with a real (small) image.

Example skeleton:

```python
# app/main.py
@app.post("/new-endpoint", response_model=NewResponse)
async def new_endpoint(file: UploadFile) -> NewResponse:
    t0 = time.monotonic()
    result = ocr.run(await file.read())
    return NewResponse(
        result=result,
        duration_ms=int((time.monotonic() - t0) * 1000),
        model=ocr.MODEL_ID,
    )
```

## Adding a UI component  <a id="frontend"></a>

1. Drop the new component in `src/components/`.
2. Keep state in `App.tsx` (the state machine: `idle | processing | result`).
   Components are presentational; props in, callbacks out.
3. Use plain CSS or CSS Modules (`Component.module.css`). No Tailwind until
   the UI grows enough to justify it.
4. API calls go through `src/api.ts` — do not call `fetch` directly from
   components. Keeps error handling and request shaping in one place.

## Tests

- **Backend**: `pytest` in `doc-extract-api/`. Tests hit the real model on
  small sample images; no mocking the model. If a test takes > 60 s, mark it
  `@pytest.mark.slow` and exclude from the default run.
- **Frontend**: not set up yet. When added, use Vitest + Testing Library.
- **End-to-end**: `docker compose up`, then a script that uploads a known
  sample and asserts the response. Live in `scripts/e2e.sh` once needed.

## Commit conventions

Conventional Commits, lowercase scope:

```
feat(api): add /extract endpoint
fix(web): handle network errors in api.ts
docs: expand CLAUDE.md with model loading gotchas
chore(deps): bump transformers to 4.45.x
```

Keep commits small and self-contained. Each commit should leave the project
in a working state.

## Working with AI agents

If you're using Claude Code (or another AI agent) to contribute:

1. Read [CLAUDE.md](CLAUDE.md) first — it's the canonical project context.
2. Run the spike (`scratch/spike.py`) before letting the agent write service
   code, especially if the model choice has changed.
3. The agent should not add CORS middleware, fake progress bars, or load the
   model per-request. CLAUDE.md spells out the "don'ts" — refer back if the
   agent suggests one of them.

## Reporting issues

Until the project is on a public host, file issues against your local fork
or note them in `TODOS.md` at the repo root.
