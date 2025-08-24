# Test PDFs Directory

This directory contains PDF files for testing the document embedding CLI functionality.

## Purpose

These PDFs are used to test the complete end-to-end workflow:
1. Upload PDF to Extralit workspace
2. Extract text content using PyMuPDF
3. Chunk the markdown content
4. Generate embeddings using OpenAI API
5. Store chunks and embeddings in Elasticsearch dataset

## Instructions for Testing

### Step 1: Add a Test PDF
Place a PDF file in this directory. Recommended test files:
- Scientific papers (for testing academic content)
- Technical documentation (for testing structured content)
- Multi-section documents (for testing hierarchy preservation)

**Suggested filename**: `test_document.pdf`

### Step 2: Upload to Extralit Workspace
Use the Extralit CLI or web interface to upload the PDF to a test workspace:

```bash
# Create a test workspace (if not exists)
extralit workspaces create --name "test_embedding"

# Upload the PDF
extralit documents add --workspace "test_embedding" --file ./test_pdfs/test_document.pdf --reference "test_doc_001"
```

### Step 3: Run Embedding Test
Once the PDF is uploaded and processed, run the embedding command:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your_openai_api_key_here"

# Run the embedding command
extralit documents embed --workspace "test_embedding" --reference "test_doc_001"

# Or with custom options
extralit documents embed \
  --workspace "test_embedding" \
  --reference "test_doc_001" \
  --dataset "test_chunks" \
  --chunk-size 800 \
  --overlap 150 \
  --dry-run
```

### Step 4: Verify Results
Check that:
- ✅ Document was found in the workspace
- ✅ Markdown content was extracted
- ✅ Chunks were created with proper hierarchy
- ✅ Embeddings were generated successfully
- ✅ Records were stored in the dataset

## Test File Recommendations

### Good Test PDFs:
- **Research papers**: Multi-section structure with abstracts, methodology, results
- **Technical manuals**: Clear hierarchy with numbered sections
- **Reports**: Executive summaries, detailed sections, conclusions

### Characteristics to Test:
- **Headers**: Multiple levels (H1, H2, H3, etc.)
- **Content variety**: Text, tables, references
- **Length**: 5-20 pages for comprehensive testing
- **Structure**: Well-organized sections and subsections

## Expected Outputs

After successful embedding, you should see:
1. **Chunks**: Text segments preserving document hierarchy
2. **Metadata**: Header information, page numbers, chunk indices
3. **Embeddings**: 1536-dimensional vectors for each chunk
4. **Dataset records**: Structured data ready for search and analysis

## Troubleshooting

### Common Issues:
1. **No documents found**: Verify workspace name and reference
2. **No markdown content**: Ensure PDF was processed by PyMuPDF
3. **Embedding failures**: Check OpenAI API key and rate limits
4. **CLI errors**: Use direct Python testing if CLI has issues

### Alternative Testing:
If CLI has compatibility issues, use the test scripts:
```bash
cd tests/embed_integration
python test_real_workflow.py
```

## Files in This Directory

- `README.md`: This file
- `test_document.pdf`: Your test PDF (add this file)
- `test_real_workflow.py`: Integration test script
- `sample_content.md`: Sample markdown for testing chunking

---

**Note**: Remember to set your `OPENAI_API_KEY` environment variable before running embedding tests that require actual API calls.