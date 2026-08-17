from extralit_server.api.schemas.v1.document.metadata import DocumentProcessingMetadata

FAILED_ROTATION = {
    "processing_time": 1.5,
    "ocr_applied": False,
    "rotation_ran": False,
    "error": "ocrmypdf exited with 2",
}


class TestUpdatePreprocessingResults:
    def test_retains_the_rotation_outcome(self):
        metadata = DocumentProcessingMetadata()

        metadata.update_preprocessing_results(FAILED_ROTATION)

        assert metadata.preprocessing_metadata.rotation_ran is False
        assert metadata.preprocessing_metadata.error == "ocrmypdf exited with 2"

    def test_the_outcome_survives_serialization_into_documents_metadata(self):
        metadata = DocumentProcessingMetadata()
        metadata.update_preprocessing_results(FAILED_ROTATION)

        stored = metadata.model_dump()["preprocessing_metadata"]

        assert stored["rotation_ran"] is False
        assert stored["error"] == "ocrmypdf exited with 2"

    def test_a_job_result_without_rotation_fields_leaves_them_unset(self):
        metadata = DocumentProcessingMetadata()

        metadata.update_preprocessing_results({"processing_time": 0.2, "ocr_applied": False})

        assert metadata.preprocessing_metadata.rotation_ran is None
        assert metadata.preprocessing_metadata.error is None
