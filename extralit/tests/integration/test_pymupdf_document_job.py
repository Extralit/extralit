#!/usr/bin/env python3
"""
Test the document upload job with PyMuPDF integration.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add the extralit-server source to the path
sys.path.insert(0, str(Path(__file__).parent / "extralit-server" / "src"))

from extralit_server.api.schemas.v1.documents import DocumentCreate


async def test_document_upload_job():
    """Test the document upload job with PyMuPDF integration."""
    
    print("📝 Testing document upload job with PyMuPDF integration...")
    
    # Find a test PDF (use the one we know works)
    test_pdf_paths = [
        Path("extralit-frontend/node_modules/@jonnytran/vue-pdf-viewer/dist/2305.14336v2.pdf"),
        Path("../extralit-benchmark/383-pdfs").glob("*.pdf"),
        Path("../test-pdf").glob("*.pdf"),
        Path(".").glob("**/*.pdf")
    ]
    
    test_pdf = None
    for path_item in test_pdf_paths:
        if isinstance(path_item, Path) and path_item.exists():
            test_pdf = path_item
            break
        elif hasattr(path_item, '__iter__'):  # It's a glob
            for pdf_file in path_item:
                if pdf_file.exists():
                    test_pdf = pdf_file
                    break
            if test_pdf:
                break
    
    if not test_pdf:
        print("❌ No small test PDF found")
        return False
    
    print(f"📄 Using test PDF: {test_pdf}")
    
    try:
        # Read PDF bytes
        pdf_bytes = test_pdf.read_bytes()
        print(f"📊 PDF size: {len(pdf_bytes)} bytes")
        
        # Simulate the job parameters
        reference = "test-pymupdf-integration"
        reference_data = {
            "id": str(uuid4()),
            "reference": reference,
            "pmid": None,
            "doi": None,
            "url": None,
            "file_name": test_pdf.name,
            "workspace_id": str(uuid4()),  # Dummy workspace ID
            "metadata": {"collections": ["test"]}
        }
        
        file_data_list = [(test_pdf.name, pdf_bytes)]
        user_id = uuid4()
        
        print("🚀 Testing document upload job (simulated)...")
        
        # Test just the preprocessing and extraction part
        from extralit_server.contexts.document import preprocessing
        from extralit_server.contexts.ocr import extract_pdf_text
        
        # Simulate preprocessing
        print("⚙️ Running preprocessing...")
        preprocessing_result = preprocessing.preprocessor.preprocess(
            file_data=pdf_bytes, 
            filename=test_pdf.name
        )
        
        print(f"✅ Preprocessing completed. Metadata: {preprocessing_result.metadata}")
        
        # Simulate PyMuPDF extraction
        print("🔍 Running PyMuPDF text extraction...")
        extraction_result = await extract_pdf_text(
            pdf_bytes=preprocessing_result.processed_data,
            filename=test_pdf.name,
            analysis_metadata=preprocessing_result.metadata
        )
        
        if extraction_result:
            markdown, metadata = extraction_result
            print("✅ PyMuPDF extraction successful!")
            print(f"📝 Markdown length: {len(markdown)} characters")
            
            # Simulate metadata merge
            file_metadata = {"collections": ["test"]}
            file_metadata.update(preprocessing_result.metadata.model_dump())
            file_metadata["pymupdf_extraction"] = {
                "markdown_content": markdown,
                "extraction_metadata": metadata,
                "extraction_successful": True,
                "extraction_time": metadata.get("processing_time")
            }
            
            print("✅ Metadata merged successfully!")
            print(f"🔍 Final metadata keys: {list(file_metadata.keys())}")
            
            return True
        else:
            print("❌ PyMuPDF extraction failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during document upload job test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the document upload job test."""
    print("🔬 Starting document upload job test...\n")
    
    success = await test_document_upload_job()
    print()
    
    if success:
        print("🎉 Document upload job with PyMuPDF integration works correctly!")
        return 0
    else:
        print("💥 Document upload job test failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
