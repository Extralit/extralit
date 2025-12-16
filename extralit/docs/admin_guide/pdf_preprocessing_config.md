# PDF Preprocessing Configuration Guide

This guide explains how to configure PDF preprocessing in Extralit Server using the `PDFPreprocessingSettings` class for optimal results with different document types.

## Overview

Extralit Server uses [OCRmyPDF](https://github.com/ocrmypdf/ocrmypdf) for PDF preprocessing, which performs OCR (Optical Character Recognition), rotation correction, optimization, and cleanup. The preprocessing pipeline also includes PDF layout analysis to extract margin and structure information.

All settings can be configured via environment variables with the `PREPROCESSING_` prefix.

## Quick Start

### Digital Research Papers (Born-Digital PDFs)

For modern PDFs that already contain searchable text:

```bash
# Minimal processing - just analysis and optimization
PREPROCESSING_ENABLED=true
PREPROCESSING_ENABLE_ANALYSIS=true
PREPROCESSING_SKIP_TEXT=true           # Skip OCR on text pages
PREPROCESSING_FORCE_OCR=false
PREPROCESSING_TESSERACT_TIMEOUT=0      # No timeout (not "skip OCR")
PREPROCESSING_OPTIMIZE=1               # Lossless optimization
PREPROCESSING_CLEAN=false              # No cleanup needed
PREPROCESSING_DESKEW=false             # Usually not needed
```

**Performance:** ~0.5-2s per page (mostly analysis)

### Scanned Research Papers (Image-Based PDFs)

For scanned documents or image-only PDFs that need OCR:

```bash
# Full OCR processing
PREPROCESSING_ENABLED=true
PREPROCESSING_ENABLE_ANALYSIS=true
PREPROCESSING_FORCE_OCR=true           # OCR all pages
PREPROCESSING_SKIP_TEXT=false          # Process text layers
PREPROCESSING_TESSERACT_TIMEOUT=180    # 3 minutes per page
PREPROCESSING_LANGUAGE=["eng"]         # Add more as needed
PREPROCESSING_ROTATE_PAGES=true        # Auto-rotate pages
PREPROCESSING_DESKEW=true              # Fix skewed scans
PREPROCESSING_CLEAN=true               # Remove scan artifacts
PREPROCESSING_OPTIMIZE=2               # Lossy compression
```

**Performance:** ~2-5s per page for good quality scans

### Mixed Document Collections

For collections with both digital and scanned papers:

```bash
# Balanced approach
PREPROCESSING_ENABLED=true
PREPROCESSING_ENABLE_ANALYSIS=true
PREPROCESSING_SKIP_TEXT=true           # Only OCR image pages
PREPROCESSING_FORCE_OCR=false          # Detect existing text
PREPROCESSING_REDO_OCR=false           # Don't re-OCR
PREPROCESSING_TESSERACT_TIMEOUT=120    # 2 minutes timeout
PREPROCESSING_ROTATE_PAGES=true
PREPROCESSING_DESKEW=false
PREPROCESSING_CLEAN=true
PREPROCESSING_OPTIMIZE=1
```

## Configuration Reference

### Core Settings

#### `PREPROCESSING_ENABLED`
- **Type**: `bool`
- **Default**: `true`
- **Description**: Master switch for PDF preprocessing. When `false`, only layout analysis runs (if `enable_analysis=true`).
- **Use Case**: Set to `false` to disable all OCR processing while keeping layout analysis.

#### `PREPROCESSING_ENABLE_ANALYSIS`
- **Type**: `bool`
- **Default**: `true`
- **Description**: Enable PDF layout analysis and margin detection using `PDFAnalyzer`.
- **Use Case**: Disable if you don't need structural metadata extraction.

### OCR Settings

#### `PREPROCESSING_LANGUAGE`
- **Type**: `list[str]`
- **Default**: `["eng"]`
- **Options**: ISO 639-3 language codes (e.g., `["eng", "spa", "fra", "deu"]`)
- **Description**: Languages for OCR recognition. Multiple languages increase processing time.
- **Use Case**:
  - Single language papers: `["eng"]`
  - Multilingual papers: `["eng", "spa"]`
  - International collections: Add all expected languages

#### `PREPROCESSING_TESSERACT_TIMEOUT`
- **Type**: `int` (seconds)
- **Default**: `0`
- **Description**: Timeout for Tesseract OCR per page. **`0` means no timeout** (unlimited time), not "skip OCR". To skip OCR entirely, set `PREPROCESSING_ENABLED=false`.
- **Use Case**:
  - `0`: No timeout - best for accuracy (default)
  - `60-120`: Standard scanned papers with time constraints
  - `180-300`: Complex layouts, low-quality scans
  - `600+`: Historical documents, very poor scan quality

#### `PREPROCESSING_FORCE_OCR`
- **Type**: `bool`
- **Default**: `false`
- **Description**: Force OCR on all pages, even those with existing text.
- **Use Case**:
  - `true`: Scanned documents, poor existing OCR
  - `false`: Digital PDFs, mixed collections (recommended)

#### `PREPROCESSING_SKIP_TEXT`
- **Type**: `bool`
- **Default**: `true`
- **Description**: Skip OCR on pages that already have text. Only process image-only pages.
- **Use Case**:
  - `true`: Digital PDFs, mixed collections (recommended)
  - `false`: Force OCR on all pages

#### `PREPROCESSING_REDO_OCR`
- **Type**: `bool`
- **Default**: `false`
- **Description**: Redo OCR on pages that already have OCR text.
- **Use Case**: Set to `true` only if existing OCR is poor quality.

### Page Processing

#### `PREPROCESSING_ROTATE_PAGES`
- **Type**: `bool`
- **Default**: `true`
- **Description**: Auto-rotate pages with horizontal text to correct orientation.
- **Use Case**: Keep `true` for scanned documents; safe for digital PDFs.

#### `PREPROCESSING_ROTATE_PAGES_THRESHOLD`
- **Type**: `float`
- **Default**: `2.0`
- **Description**: Confidence threshold for rotation (higher = more conservative).
- **Use Case**: Lower (1.0-1.5) for aggressive rotation; higher (3.0+) to avoid false rotations.

#### `PREPROCESSING_DESKEW`
- **Type**: `bool`
- **Default**: `false`
- **Description**: Correct skewed/tilted text in scanned documents.
- **Use Case**:
  - `true`: Scanned documents with visible skew
  - `false`: Digital PDFs (adds processing time)

#### `PREPROCESSING_CLEAN`
- **Type**: `bool`
- **Default**: `true`
- **Description**: Use `unpaper` to remove scan artifacts, borders, and noise.
- **Use Case**:
  - `true`: Scanned documents, photocopies
  - `false`: Clean digital PDFs (saves processing time)

### Output Optimization

#### `PREPROCESSING_OPTIMIZE`
- **Type**: `int`
- **Default**: `1`
- **Options**:
  - `0`: No optimization (largest file size)
  - `1`: Lossless optimization (recommended for digital PDFs)
  - `2`: Lossy compression (good for scanned documents)
  - `3`: Aggressive compression (smallest size, some quality loss)
- **Use Case**:
  - Digital PDFs: `1` (preserve quality)
  - Scanned documents: `2` (balance size/quality)
  - Large collections: `3` (minimize storage)

#### `PREPROCESSING_PDF_RENDERER`
- **Type**: `str`
- **Default**: `"hocr"`
- **Options**: `"auto"`, `"hocr"`, `"sandwich"`
- **Description**:
  - `"hocr"`: Embed invisible text layer (best for most documents)
  - `"sandwich"`: Visible text with image background (preserves appearance)
  - `"auto"`: Let OCRmyPDF choose
- **Use Case**:
  - Digital papers: `"hocr"` (smaller files)
  - Scanned papers: `"hocr"` or `"sandwich"` (depending on preference)

#### `PREPROCESSING_OUTPUT_TYPE`
- **Type**: `str`
- **Default**: `"pdf"`
- **Options**: `"pdf"`, `"pdfa"`, `"pdfa-1"`, `"pdfa-2"`, `"pdfa-3"`
- **Description**: Output PDF format. `"pdf"` skips PDF/A conversion.
- **Use Case**: Use `"pdf"` for speed; PDF/A formats for long-term archival.

#### `PREPROCESSING_FAST_WEB_VIEW`
- **Type**: `int`
- **Default**: `999999` (effectively disabled)
- **Description**: Optimize PDF for web viewing by reorganizing structure. High values disable optimization.
- **Use Case**: Set to `1` for web-served PDFs; keep default for processing pipelines.

### Performance Settings

#### `PREPROCESSING_JOBS`
- **Type**: `int`
- **Default**: `1`
- **Description**: Number of parallel worker processes for OCR.
- **Use Case**:
  - Docker/limited CPU: `1` (avoid oversubscription)
  - Multi-core servers: `2-4` (balance speed/resources)
  - High-memory systems: `4-8` (maximum parallelism)

#### `PREPROCESSING_SKIP_BIG`
- **Type**: `float` (MB)
- **Default**: `100.0`
- **Description**: Skip OCR on images larger than this threshold to avoid timeouts.
- **Use Case**:
  - High-quality scans: `50-100` MB
  - Standard documents: `100-200` MB
  - Large format papers: `200+` MB

#### `PREPROCESSING_PROGRESS_BAR`
- **Type**: `bool`
- **Default**: `false`
- **Description**: Show progress bar during processing (useful for CLI, not for background jobs).
- **Use Case**: `true` for interactive processing; `false` for production.

## Troubleshooting

### Issue: Timeout Errors

**Symptoms**: `TesseractTimeout` errors in logs

**Solutions**:
1. Increase `PREPROCESSING_TESSERACT_TIMEOUT` (try 300-600)
2. Increase `PREPROCESSING_SKIP_BIG` to skip problematic pages
3. Reduce `PREPROCESSING_JOBS` to avoid resource contention
4. Set `PREPROCESSING_CLEAN=false` to skip image preprocessing

### Issue: Poor OCR Quality

**Symptoms**: Garbled or missing text extraction

**Solutions**:
1. Enable `PREPROCESSING_DESKEW=true` for skewed scans
2. Enable `PREPROCESSING_CLEAN=true` to remove artifacts
3. Set `PREPROCESSING_FORCE_OCR=true` to redo existing OCR
4. Add more languages to `PREPROCESSING_LANGUAGE`
5. Adjust `PREPROCESSING_ROTATE_PAGES_THRESHOLD` if pages are incorrectly rotated

### Issue: Processing Too Slow

**Symptoms**: Long wait times for document processing

**Solutions**:
1. Set `PREPROCESSING_ENABLED=false` for digital PDFs (only run analysis)
2. Reduce `PREPROCESSING_TESSERACT_TIMEOUT` (try 60-120)
3. Ensure `PREPROCESSING_SKIP_TEXT=true` for hybrid documents
4. Reduce `PREPROCESSING_OPTIMIZE` level
5. Disable `PREPROCESSING_CLEAN=false` and `PREPROCESSING_DESKEW=false`

### Issue: High Memory Usage

**Symptoms**: Out-of-memory errors, system slowdown

**Solutions**:
1. Set `PREPROCESSING_JOBS=1` (most important)
2. Reduce `PREPROCESSING_SKIP_BIG` threshold (e.g., 50 MB)
3. Set `PREPROCESSING_OPTIMIZE=3` to reduce output size
4. Process documents in smaller batches

## Integration Examples

### Programmatic Configuration (Python)

```python
from extralit_server.contexts.document.preprocessing import (
    PDFPreprocessor,
    PDFPreprocessingSettings
)

# Custom settings for scanned documents
settings = PDFPreprocessingSettings(
    enabled=True,
    enable_analysis=True,
    force_ocr=True,
    tesseract_timeout=180,
    language=["eng"],
    deskew=True,
    clean=True,
    optimize=2
)

preprocessor = PDFPreprocessor(settings=settings)
result = preprocessor.preprocess(pdf_bytes, "document.pdf")

# Access processed data and metadata
processed_pdf = result.processed_data
metadata = result.metadata
print(f"Processing time: {metadata.processing_time:.2f}s")
print(f"Analysis results: {metadata.analysis_results}")
```

### Environment Variables (Docker/Production)

Create a `.env` file:

```bash
# Extralit Server Configuration
EXTRALIT_DATABASE_URL=postgresql://user:pass@localhost/extralit
EXTRALIT_REDIS_URL=redis://localhost:6379/0

# PDF Preprocessing for Scanned Documents
PREPROCESSING_ENABLED=true
PREPROCESSING_ENABLE_ANALYSIS=true
PREPROCESSING_FORCE_OCR=true
PREPROCESSING_TESSERACT_TIMEOUT=180
PREPROCESSING_LANGUAGE=["eng", "spa"]
PREPROCESSING_DESKEW=true
PREPROCESSING_CLEAN=true
PREPROCESSING_OPTIMIZE=2
PREPROCESSING_JOBS=2
```

## Related Components

| File | Purpose |
|------|---------|
| [`preprocessing.py`](../src/extralit_server/contexts/document/preprocessing.py) | Core preprocessing logic and settings |
| [`margin.py`](../src/extralit_server/contexts/document/margin.py) | PDF layout analysis and margin detection |
| [`api/schemas/v1/document/preprocessing.py`](../src/extralit_server/api/schemas/v1/document/preprocessing.py) | API metadata schema |

## Important Notes

1. **Environment Variables**: All settings can be overridden via `PREPROCESSING_*` env vars
2. **OCRmyPDF Dependency**: Requires `ocrmypdf` and `tesseract` installed
3. **Lazy Loading**: `ocrmypdf` is lazy-loaded to avoid import overhead
4. **Error Handling**: Falls back to temp files if BytesIO approach fails

## Further Reading

- [OCRmyPDF Documentation](https://ocrmypdf.readthedocs.io/)
- [Tesseract Language Data](https://github.com/tesseract-ocr/tessdata)
- [PDF/A Archival Standards](https://en.wikipedia.org/wiki/PDF/A)
- [Extralit Server Architecture](../README.md)

## Related Repositories

- [Extralit](https://github.com/Extralit/extralit)
- [Extralit HF Space](https://github.com/Extralit/extralit-hf-space)
- [Papers OCR Benchmarks](https://github.com/Extralit/papers-ocr-benchmarks)
