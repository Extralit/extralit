# Extralit Tools

This directory contains utility scripts and tools for testing and development.

## PyMuPDF Performance Test

**File:** `pymupdf_performance_test.py`

**Purpose:** Comprehensive performance testing for the PyMuPDF extraction service integration.

**Features:**
- Apache Bench equivalent testing (`ab -n 5 -c 5`)
- Tests multiple PDFs with detailed metrics
- Generates documentation-ready performance statistics
- Interactive mode selection

**Usage:**
```bash
# From extralit root directory
cd tools
python pymupdf_performance_test.py

# Choose mode:
# 1. Test single PDF (equivalent to ab -n 5 -c 5)
# 2. Test all PDFs comprehensively
```

**Requirements:**
- extralit-hf-space server running on localhost:7860
- Python requests library
- Test PDFs in ../test-pdf/ directory

**Sample Output:**
```
Performance
✅ Processes 0.3-0.4MB, 1-2 page research papers in ~8-13 seconds
✅ Extracts 16,915-68,344+ characters of structured markdown
✅ Handles concurrent requests efficiently (5 concurrent connections)
✅ Memory efficient with proper cleanup
✅ 100% success rate across all test scenarios
```
