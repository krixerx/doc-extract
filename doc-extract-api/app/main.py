"""FastAPI app for doc-extract.

No CORS middleware — the nginx proxy makes the frontend same-origin in prod,
and Vite's dev server proxies /api during local dev. See CLAUDE.md.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app import ocr
from app.schemas import ErrorResponse, HealthResponse, OcrResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_PDF_PAGES = 10  # GOT-OCR is ~1-3 min/page on CPU — cap keeps requests within nginx timeout
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff"}
PDF_CONTENT_TYPES = {"application/pdf"}
ALLOWED_CONTENT_TYPES = IMAGE_CONTENT_TYPES | PDF_CONTENT_TYPES


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup — loading OCR engine")
    ocr.load_engine()
    yield
    logger.info("Shutdown")


app = FastAPI(
    title="doc-extract-api",
    description="Self-hosted OCR microservice using GOT-OCR 2.0.",
    version="0.1.0",
    lifespan=lifespan,
)


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(error=message, code=code).model_dump(),
    )


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    """Liveness/readiness probe. Returns 200 once model weights are in memory."""
    return HealthResponse(
        status="ok" if ocr.is_loaded() else "loading",
        model=ocr.MODEL_ID,
        model_loaded=ocr.is_loaded(),
    )


@app.post(
    "/ocr",
    response_model=OcrResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    tags=["ocr"],
)
async def post_ocr(file: UploadFile = File(...)) -> OcrResponse:
    """Extract raw text from an uploaded document image."""
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Unsupported content type: {file.content_type}", "code": "unsupported_type"},
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail={"error": "Empty file", "code": "empty_file"})
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"error": f"File exceeds {MAX_UPLOAD_BYTES} bytes", "code": "file_too_large"},
        )

    is_pdf = file.content_type in PDF_CONTENT_TYPES or data[:4] == b"%PDF"
    try:
        if is_pdf:
            pages, duration_ms = ocr.run_ocr_pdf(data, max_pages=MAX_PDF_PAGES)
        else:
            pages, duration_ms = ocr.run_ocr_image(data)
    except ocr.PdfTooManyPagesError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"PDF has {exc.page_count} pages; max is {exc.max_pages}",
                "code": "pdf_too_many_pages",
            },
        ) from exc
    except Exception as exc:  # noqa: BLE001 — surface as 500 with code
        logger.exception("OCR inference failed")
        raise HTTPException(
            status_code=500,
            detail={"error": str(exc), "code": "inference_failure"},
        ) from exc

    return OcrResponse(
        text="\n\n".join(pages),
        pages=pages,
        page_count=len(pages),
        duration_ms=duration_ms,
        model=ocr.MODEL_ID,
    )
