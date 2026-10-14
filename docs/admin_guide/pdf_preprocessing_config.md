# PDF Preprocessing Configuration Guide

Extralit Server runs [OCRmyPDF](https://github.com/ocrmypdf/ocrmypdf) over every uploaded PDF for
**page rotation only**. No OCR text is produced: `tesseract_timeout=0` kills the tesseract OCR
spawn and `skip_text` leaves pages that already have text untouched. The one thing tesseract is
still asked for is OSD — deciding whether a page is sideways — which is why its budget is bounded.

Settings live in `PDFPreprocessingSettings` and are configurable via `PREPROCESSING_`-prefixed
environment variables.

## What runs on an upload

| Step | Component | Output |
|---|---|---|
| Triage | `contexts/ocr/triage.py` (pdf-inspector) | `pdf_type`, `pages_needing_ocr`, `pages_with_tables`, `pages_with_columns`, encoding issues |
| Margins + thumbnail | `contexts/document/margin.py` (`PDFAnalyzer`) | `analysis_metadata.layout_analysis.margin_analysis`, thumbnail object |
| Rotation | `contexts/document/preprocessing.py` (ocrmypdf) | the PDF rewritten at the same key |
| Layout | `jobs/ocr_jobs.py` | canonical `DoclingDocument` JSON + the workspace's Lance rows |

Triage classifies which pages have no usable text, but pdf-inspector bundles no OCR engine and
tesseract OCR is off, so those pages are **surfaced, not fixed**: they appear in
`analysis_metadata.triage.pages_needing_ocr` and `layout_metadata.pages_needing_ocr` and stay an
explicit gap until an OCR job exists.

## Configuration Reference

### `PREPROCESSING_ENABLED`
- **Type**: `bool` — **Default**: `true`
- Master switch. When `false`, the PDF is passed through byte-identical; triage, margins and the
  thumbnail still run (they are the analysis job's own work, not the preprocessor's).

### `PREPROCESSING_ROTATE_PAGES`
- **Type**: `bool` — **Default**: `true`
- Auto-rotate pages whose text is not upright.

### `PREPROCESSING_ROTATE_PAGES_THRESHOLD`
- **Type**: `float` — **Default**: `2.0`
- Confidence OSD must reach before a page is rotated. Lower (1.0–1.5) rotates more eagerly;
  higher (3.0+) avoids false rotations.

### `PREPROCESSING_TESSERACT_NON_OCR_TIMEOUT`
- **Type**: `float` (seconds per page) — **Default**: `30.0`
- Budget for OSD, the only tesseract call made here. OCRmyPDF's own default is 180 s per page,
  which dominates the runtime on image-heavy PDFs.

### `PREPROCESSING_JOBS`
- **Type**: `int` — **Default**: `1`
- Worker processes for ocrmypdf. Keep at `1` in containers with limited CPU to avoid
  oversubscription; `2–4` on a multi-core host.

### `PREPROCESSING_PROGRESS_BAR`
- **Type**: `bool` — **Default**: `false`
- Useful interactively, noise in background jobs.

### Fixed, not configurable

`skip_text=True`, `tesseract_timeout=0`, `clean=False`, `optimize=0`. These are what make the pass
rotation-only: `clean` (unpaper) and `optimize` only pay off alongside OCR output, and the
alternatives that would OCR image pages are destructive — `force_ocr` rasterizes the existing text
layer, and `redo_ocr` strips invisible OCR text it cannot regenerate with tesseract disabled.

### Known limit

Verified in `ocrmypdf/_pipeline.py::is_ocr_required`: under `skip_text`, OSD only runs on pages
ocrmypdf would process, i.e. image-only pages. A born-digital page keeps whatever `/Rotate` it
already has. A text-only PDF still pays pdfinfo, a re-save and the S3 rewrite — cheap, and nothing
is rasterized.

## Troubleshooting

### Rotation is slow on scanned PDFs

OSD is the cost. Lower `PREPROCESSING_TESSERACT_NON_OCR_TIMEOUT`, or set
`PREPROCESSING_ROTATE_PAGES=false` to skip orientation detection entirely.

### A page is rotated the wrong way

Raise `PREPROCESSING_ROTATE_PAGES_THRESHOLD` so OSD needs more confidence before acting.

### Rotation failed

The job records it and keeps going: the original bytes are stored, and
`preprocessing_metadata.rotation_ran` is `false` with the reason in `preprocessing_metadata.error`.
Nothing downstream is blocked, because layout and text extraction depend on this job with
`allow_failure`.

### High memory usage

Set `PREPROCESSING_JOBS=1`. Rotation itself holds one page image at a time.

## Integration Example

```python
from extralit_server.contexts.document.preprocessing import (
    PDFPreprocessingSettings,
    PDFPreprocessor,
)

settings = PDFPreprocessingSettings(rotate_pages=True, tesseract_non_ocr_timeout=15.0, jobs=2)
result = PDFPreprocessor(settings).preprocess(pdf_bytes, "document.pdf")

print(result.metadata.rotation_ran, result.metadata.processing_time, result.metadata.error)
processed_pdf = result.processed_data
```

## Related Components

| File | Purpose |
|------|---------|
| [`preprocessing.py`](../../extralit-server/src/extralit_server/contexts/document/preprocessing.py) | The rotation pass and its settings |
| [`triage.py`](../../extralit-server/src/extralit_server/contexts/ocr/triage.py) | Structural classification (pdf-inspector) |
| [`margin.py`](../../extralit-server/src/extralit_server/contexts/document/margin.py) | Margin detection and thumbnail, over the leading pages |
| [`document/metadata.py`](../../extralit-server/src/extralit_server/api/schemas/v1/document/metadata.py) | What lands in `documents.metadata_` |

## Further Reading

- [OCRmyPDF Documentation](https://ocrmypdf.readthedocs.io/)
- [Extralit](https://github.com/Extralit/extralit)
- [Extralit HF Space](https://github.com/Extralit/extralit-hf-space)
- [Papers OCR Benchmarks](https://github.com/Extralit/papers-ocr-benchmarks)
