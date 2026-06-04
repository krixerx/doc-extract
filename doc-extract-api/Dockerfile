# doc-extract-api — FastAPI + GOT-OCR 2.0 (CPU)
#
# Multi-stage isn't used here on purpose: the model weights are downloaded at
# build time so the container is ready the moment it starts (see
# docs/ARCHITECTURE.md "pre-download model weights").

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/huggingface \
    TRANSFORMERS_CACHE=/opt/huggingface

WORKDIR /app

# System deps for PyTorch + image processing (libgl, libglib are required for
# Pillow/OpenCV runtime — missing these = cryptic ImportError on first request).
# poppler-utils provides pdftoppm/pdfinfo, required by pdf2image for PDF input.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# PyTorch CPU wheels first (much smaller than the default CUDA-bundled wheels)
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
        torch==2.5.1 \
        torchvision==0.20.1

COPY requirements.txt .
RUN pip install -r requirements.txt

# Pre-download model weights so the container is ready at startup
RUN python -c "from transformers import AutoModel, AutoTokenizer; \
    AutoTokenizer.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True); \
    AutoModel.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True, low_cpu_mem_usage=True, use_safetensors=True)"

COPY app/ ./app/

EXPOSE 8000

# Single worker — the model is large; running multiple workers would multiply RAM
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
