# Extralit Document Embedding CLI - Testing Suite

This directory contains comprehensive tests for the document embedding CLI functionality.

## 📁 Directory Structure

```
tests/
├── README.md                           # This file
├── test_import.py                      # Basic import functionality test
├── test_embed_functionality.py        # Comprehensive unit tests (mocked)
├── test_embedding_debug.py            # Debug tests for OpenAI integration
├── demo_embed_usage.py                # Complete workflow demonstration
└── embed_integration/                 # Real-world integration tests
    ├── test_real_workflow.py          # End-to-end testing with real data
    ├── sample_content.md               # Sample markdown for chunking tests
    └── test_pdfs/                      # Directory for test PDF files
        └── README.md                   # Instructions for PDF testing
```

## 🧪 Test Categories

### 1. Unit Tests (Mocked)
**File**: `test_embed_functionality.py`
- Tests chunking algorithm with sample content
- Tests embedding creation (mocked OpenAI API)
- Tests record creation and structure
- Tests complete workflow integration
- **Status**: ✅ All 4 tests passing

### 2. Integration Tests (Real APIs)
**File**: `embed_integration/test_real_workflow.py`
- Tests with real Extralit client
- Tests with real workspace and documents
- Tests with real OpenAI API calls
- Comprehensive error handling and validation

### 3. Debug Tests
**File**: `test_embedding_debug.py`
- Isolates OpenAI API integration issues
- Tests llama-index component imports
- Helps diagnose authentication problems

### 4. Demonstration
**File**: `demo_embed_usage.py`
- Shows complete workflow simulation
- Realistic document processing example
- CLI options documentation
- Usage examples and best practices

## 🚀 How to Test

### Quick Test (Unit Tests)
```bash
cd extralit
venv\Scripts\activate
python tests/test_embed_functionality.py
```
**Expected**: All 4 tests should pass (100% success rate)

### Real Integration Test
```bash
cd extralit
venv\Scripts\activate

# Set your API key
export OPENAI_API_KEY="your_openai_api_key"

# Run integration test
python tests/embed_integration/test_real_workflow.py
```

### Demo Workflow
```bash
cd extralit
venv\Scripts\activate
python tests/demo_embed_usage.py
```

## 📄 Testing with Real PDFs

### Step 1: Prepare Test PDF
1. Place a PDF file in `tests/embed_integration/test_pdfs/`
2. Recommended: Scientific papers, technical docs, or structured reports
3. Size: 5-20 pages for comprehensive testing

### Step 2: Upload to Extralit Workspace
```bash
# Create test workspace
extralit workspaces create --name "test_embedding"

# Upload PDF
extralit documents add \
  --workspace "test_embedding" \
  --file tests/embed_integration/test_pdfs/your_document.pdf \
  --reference "test_doc_001"
```

### Step 3: Run Embedding Command
```bash
# Set OpenAI API key
export OPENAI_API_KEY="your_openai_api_key"

# Run embedding (dry run first)
extralit documents embed \
  --workspace "test_embedding" \
  --reference "test_doc_001" \
  --dry-run

# Run actual embedding
extralit documents embed \
  --workspace "test_embedding" \
  --reference "test_doc_001" \
  --dataset "test_chunks"
```

### Step 4: Verify Results
Check that the command:
- ✅ Found the workspace and document
- ✅ Extracted markdown content
- ✅ Created chunks with proper hierarchy
- ✅ Generated embeddings for each chunk
- ✅ Stored records in the dataset

## 🔧 Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
ModuleNotFoundError: No module named 'extralit.cli'
```
**Solution**: Run `uv pip install -e .` from the extralit/extralit directory

#### 2. OpenAI API Errors
```bash
Error code: 401 - Invalid API key
```
**Solution**: Set valid `OPENAI_API_KEY` environment variable

#### 3. No Documents Found
```bash
No documents found with reference 'test_doc'
```
**Solution**: Upload a document first using `extralit documents add`

#### 4. CLI Compatibility Issues
```bash
TypeError: Parameter.make_metavar() takes 1 positional argument but 2 were given
```
**Solution**: Use the integration test script instead of CLI directly

### Alternative Testing Methods

If CLI has issues, use direct function calls:

```python
import os
import sys
sys.path.insert(0, 'extralit/src')

from extralit.cli.documents.embed import chunk_markdown, create_embedding
from extralit.client import Extralit

# Your test code here
```

## 📊 Test Results Interpretation

### Unit Tests (test_embed_functionality.py)
- **4/4 PASS**: All functionality working correctly
- **3/4 PASS**: Minor issues, check specific test output
- **<3/4 PASS**: Significant issues, review implementation

### Integration Tests (test_real_workflow.py)
- **All components working**: Ready for production
- **Document upload needed**: Core functionality working, just need real data
- **API issues**: Check authentication and connectivity
- **Client issues**: Verify Extralit login status

## 🎯 Success Criteria

### For Unit Testing:
- [x] All imports work correctly
- [x] Chunking preserves markdown hierarchy
- [x] Embedding creation integrates with llama-index
- [x] Record structure matches expected format
- [x] Complete workflow executes without errors

### For Integration Testing:
- [ ] Extralit client initializes successfully
- [ ] Workspace and documents can be accessed
- [ ] Real documents have extracted markdown content
- [ ] OpenAI API creates actual embeddings
- [ ] Records are stored in Elasticsearch dataset
- [ ] CLI command works end-to-end

## 📋 Testing Checklist

Before considering the feature complete:

- [ ] Run `test_embed_functionality.py` - all tests pass
- [ ] Upload a test PDF to workspace
- [ ] Run `test_real_workflow.py` - integration successful
- [ ] Try CLI command with `--dry-run` - preview works
- [ ] Try CLI command with real embedding - records created
- [ ] Verify dataset contains embedded chunks
- [ ] Test with different chunk sizes and overlap settings
- [ ] Test error scenarios (missing docs, invalid API key)

## 🚀 Next Steps

Once all tests pass:

1. **Production Deployment**: Feature is ready for real-world use
2. **Documentation**: Update user guides with embedding workflow
3. **Performance Testing**: Test with large documents and datasets
4. **Monitoring**: Set up logging for production embedding jobs
5. **Optimization**: Fine-tune chunking parameters based on use cases

## 📞 Support

If you encounter issues during testing:

1. Check the troubleshooting section above
2. Review test output for specific error messages
3. Ensure all environment variables are set correctly
4. Verify Extralit login status and workspace access
5. Test with a simple PDF first before complex documents

The testing suite is designed to validate every aspect of the embedding functionality and ensure production readiness.