# Third-Party Notices

doc-extract
Copyright 2026 Erki Kriks

This product includes software developed by third parties. Their licenses
are reproduced below. All licenses are compatible with this project's
distribution under the Apache License 2.0 (see `LICENSE`), except where
noted (the verovio LGPL-3.0 obligation is described in §AI/ML).

## AI / ML stack

| Component | Version pinned | License | Source |
|---|---|---|---|
| **GOT-OCR 2.0** (model weights + bundled inference code) | `stepfun-ai/GOT-OCR2_0` | Apache 2.0 | <https://huggingface.co/stepfun-ai/GOT-OCR2_0> |
| **Transformers** | 4.46.3 | Apache 2.0 | <https://github.com/huggingface/transformers> |
| **PyTorch** (CPU) | 2.5.1 | BSD 3-Clause | <https://github.com/pytorch/pytorch> |
| **torchvision** | 0.20.1 | BSD 3-Clause | <https://github.com/pytorch/vision> |
| **accelerate** | 1.1.1 | Apache 2.0 | <https://github.com/huggingface/accelerate> |
| **tiktoken** | 0.8.0 | MIT | <https://github.com/openai/tiktoken> |
| **verovio** | 4.3.1 | **LGPL-3.0** | <https://github.com/rism-digital/verovio> |
| **NumPy** | 1.26.4 | BSD 3-Clause | <https://github.com/numpy/numpy> |
| **Pillow** | 11.0.0 | HPND (MIT-compatible) | <https://github.com/python-pillow/Pillow> |

**Note on verovio (LGPL-3.0):** verovio is pulled in as a transitive runtime
dependency by GOT-OCR for `ocr_type='format'` mode (musical notation, math).
doc-extract uses only `ocr_type='ocr'` (plain text), so verovio is loaded but
not invoked at runtime. We use the unmodified upstream Python wheel; under
LGPL-3.0 this is dynamic linking and does not impose copyleft on doc-extract's
own code. If you fork verovio and modify it, you must release the modified
verovio under LGPL-3.0.

**Note on GOT-OCR 2.0 training data:** the original GOT-OCR 2.0 GitHub
repository at `Ucas-HaoranWei/GOT-OCR2.0` dual-licenses code (Apache 2.0)
and training data (CC BY-NC 4.0). doc-extract consumes only the **trained
model weights and inference code** from HuggingFace, both released under
Apache 2.0. The CC BY-NC data license does not affect users of the trained
model.

## Backend web framework

| Component | Version pinned | License | Source |
|---|---|---|---|
| **FastAPI** | 0.115.5 | MIT | <https://github.com/fastapi/fastapi> |
| **Uvicorn** | 0.32.1 | BSD 3-Clause | <https://github.com/encode/uvicorn> |
| **Pydantic** | 2.10.3 | MIT | <https://github.com/pydantic/pydantic> |
| **python-multipart** | 0.0.20 | Apache 2.0 | <https://github.com/Kludex/python-multipart> |

## Frontend

| Component | Version pinned | License | Source |
|---|---|---|---|
| **React** | 18.3.1 | MIT | <https://github.com/facebook/react> |
| **ReactDOM** | 18.3.1 | MIT | <https://github.com/facebook/react> |
| **Vite** | 5.4.11 | MIT | <https://github.com/vitejs/vite> |
| **@vitejs/plugin-react** | 4.3.4 | MIT | <https://github.com/vitejs/vite-plugin-react> |
| **TypeScript** | 5.6.3 | Apache 2.0 | <https://github.com/microsoft/TypeScript> |

## Infrastructure

| Component | License | Source |
|---|---|---|
| **nginx** (alpine) | BSD 2-Clause | <https://nginx.org/LICENSE> |
| **Python** (Docker base image) | PSF License | <https://www.python.org/psf/license/> |
| **Debian slim** (Docker base image) | Various (mostly GPL/LGPL/BSD/MIT) | <https://www.debian.org/legal/licenses/> |
| **Node.js** (frontend build stage only) | MIT + others | <https://github.com/nodejs/node/blob/main/LICENSE> |

## License-text shortcuts

Full text of each license is available at the source links above. The most
common are reproduced inline here for reference:

- **Apache 2.0** — see `LICENSE` in this repo (also applies to doc-extract).
- **MIT** — <https://opensource.org/licenses/MIT>
- **BSD 3-Clause** — <https://opensource.org/licenses/BSD-3-Clause>
- **BSD 2-Clause** — <https://opensource.org/licenses/BSD-2-Clause>
- **LGPL-3.0** — <https://www.gnu.org/licenses/lgpl-3.0.html>
- **HPND** — <https://opensource.org/licenses/HPND>
- **CC BY-NC 4.0** (data license, does not apply to model weights) — <https://creativecommons.org/licenses/by-nc/4.0/>

## How to refresh this list

Direct dependencies are pinned in `doc-extract-api/requirements.txt` and
`doc-extract-web/package.json`. To audit transitive dependencies and their
licenses:

```bash
# Python
pip install pip-licenses
pip-licenses --from=mixed --format=markdown

# JavaScript
npx license-checker --production --summary
```

If a dependency is added or its license changes, update this file in the
same commit.
