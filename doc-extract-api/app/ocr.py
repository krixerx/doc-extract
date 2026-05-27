"""GOT-OCR 2.0 model loader and inference.

Loaded once at app startup (see main.py lifespan) and reused across requests.
Do not load the model per request — cold load is 10-30s on CPU.
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Optional

import torch

# GOT-OCR 2.0's bundled modeling_GOT.py hardcodes calls to `.cuda()` and `.half()`
# inside chat() — e.g. `torch.as_tensor(input_ids).cuda()` and an `image.half()`
# cast before the vision tower. On CPU-only deployments those raise:
#   - AssertionError: Torch not compiled with CUDA enabled
#   - RuntimeError: Input type (c10::Half) and bias type (float) should be the same
# We neuter both methods before transformers is imported so the model's chat()
# picks up the no-op versions. Tensors stay on CPU in fp32 (matches our
# `torch_dtype=torch.float32` load) — the model produces identical text output.
# CPU fp16 is poorly supported in PyTorch anyway, so disabling .half() is the
# right move here.
if not torch.cuda.is_available():
    torch.Tensor.cuda = lambda self, *args, **kwargs: self  # type: ignore[assignment]
    torch.Tensor.half = lambda self, *args, **kwargs: self  # type: ignore[assignment]
    torch.nn.Module.cuda = lambda self, *args, **kwargs: self  # type: ignore[assignment]
    torch.nn.Module.half = lambda self, *args, **kwargs: self  # type: ignore[assignment]

from transformers import AutoModel, AutoTokenizer  # noqa: E402 — must follow the cuda shim above

logger = logging.getLogger(__name__)

MODEL_ID = "stepfun-ai/GOT-OCR2_0"


@dataclass
class OcrEngine:
    """Holds the loaded model + tokenizer. Created once at startup."""

    model: object
    tokenizer: object
    model_id: str = MODEL_ID


_engine: Optional[OcrEngine] = None


def load_engine() -> OcrEngine:
    """Load the model and tokenizer. Idempotent — returns cached engine if already loaded."""
    global _engine
    if _engine is not None:
        return _engine

    logger.info("Loading tokenizer %s", MODEL_ID)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)

    logger.info("Loading model %s (CPU, low_cpu_mem_usage=True)", MODEL_ID)
    model = AutoModel.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        use_safetensors=True,
        pad_token_id=tokenizer.eos_token_id,
        torch_dtype=torch.float32,
    )
    model = model.eval()

    _engine = OcrEngine(model=model, tokenizer=tokenizer)
    logger.info("Model ready")
    return _engine


def is_loaded() -> bool:
    return _engine is not None


def run_ocr(image_bytes: bytes, ocr_type: str = "ocr") -> tuple[str, int]:
    """Run OCR on raw image bytes. Returns (text, duration_ms)."""
    if _engine is None:
        raise RuntimeError("OCR engine not loaded — call load_engine() at startup")

    # GOT-OCR's chat() API takes a file path, not bytes. Save to a temp file.
    suffix = ".png"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="ocr-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(image_bytes)

        t0 = time.monotonic()
        with torch.inference_mode():
            text = _engine.model.chat(
                _engine.tokenizer,
                tmp_path,
                ocr_type=ocr_type,
            )
        duration_ms = int((time.monotonic() - t0) * 1000)
        return text, duration_ms
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
