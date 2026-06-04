from pydantic import BaseModel, Field


class OcrResponse(BaseModel):
    text: str = Field(..., description="Full extracted text. Multi-page PDFs joined with blank lines.")
    pages: list[str] = Field(..., description="Per-page text. Length 1 for image inputs.")
    page_count: int = Field(..., description="Number of pages processed.")
    duration_ms: int = Field(..., description="Wall-clock inference time in ms.")
    model: str = Field(..., description="Model identifier used for OCR.")


class HealthResponse(BaseModel):
    status: str
    model: str
    model_loaded: bool


class ErrorResponse(BaseModel):
    error: str
    code: str
