# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Modal deployment for Datalab Marker PDF conversion service.
"""

import os
from typing import Optional

import modal

# Define the Modal app
app = modal.App("datalab-marker-modal-demo")
GPU_TYPE = "T4"
MODEL_PATH_PREFIX = "/root/.cache/datalab/models"

# Define the container image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install(["git", "wget"])
    .env({"TORCH_DEVICE": "cuda"})
    .pip_install(
        [
            "marker-pdf[full]",
            "fastapi==0.104.1",
            "uvicorn==0.24.0",
            "python-multipart==0.0.6",
            "torch>=2.2.2,<3.0.0",
            "torchvision>=0.17.0",
            "torchaudio>=2.2.0",
        ]
    )
)

# Create a persistent volume for model caching
models_volume = modal.Volume.from_name("marker-models-modal-demo", create_if_missing=True)


def setup_models_with_cache_check(logger, commit_volume=False):
    """
    Shared function to create models and handle cache checking/logging.
    """
    import gc
    import os

    from marker.models import create_model_dict

    # Check if models exist in cache
    models_dir_exists = os.path.exists(MODEL_PATH_PREFIX)
    models_dir_contents = os.listdir(MODEL_PATH_PREFIX) if models_dir_exists else []

    logger.info(f"Models cache directory exists: {models_dir_exists}")
    logger.info(f"Models cache directory contents: {models_dir_contents}")

    if models_dir_exists and models_dir_contents:
        logger.info("Found existing models in volume cache, loading from cache...")
    else:
        logger.warning(
            "No models found in volume cache. Models will be downloaded now (this may take several minutes)."
        )

    # Create/load models
    models = create_model_dict()
    logger.info(f"Successfully loaded {len(models)} models")

    # Check what was downloaded/cached
    if os.path.exists(MODEL_PATH_PREFIX):
        contents = os.listdir(MODEL_PATH_PREFIX)
        logger.info(f"Models in cache: {contents}")

    # Commit volume if requested (for download function)
    if commit_volume:
        gc.collect()
        logger.info("Attempting to commit volume...")
        models_volume.commit()
        logger.info("Volume committed successfully")

    return models


@app.function(
    image=image,
    volumes={MODEL_PATH_PREFIX: models_volume},
    gpu=GPU_TYPE,
    timeout=600,
)
def download_models():
    """
    Helper function to download models used in marker into a Modal volume.
    """
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Downloading models to persistent volume...")
    logger.info(f"Volume mounted at: {MODEL_PATH_PREFIX}")

    try:
        models = setup_models_with_cache_check(logger, commit_volume=True)
        return f"Models downloaded successfully: {list(models.keys())}"
    except Exception as e:
        logger.error(f"Failed to download models: {e}")
        raise


@app.cls(
    image=image,
    gpu=GPU_TYPE,
    memory=16384,
    timeout=600,  # 10 minute timeout for large documents
    volumes={MODEL_PATH_PREFIX: models_volume},
    scaledown_window=300,
)
class MarkerModalDemoService:
    @modal.enter()
    def load_models(self):
        """Load models once per container using @modal.enter() for efficiency."""
        import logging
        import traceback

        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        logger = logging.getLogger(__name__)

        logger.info("Loading Marker models using @modal.enter()...")
        try:
            self.models = setup_models_with_cache_check(logger, commit_volume=True)
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            traceback.print_exc()
            self.models = None

    @modal.asgi_app()
    def marker_api(self):
        import base64
        import io
        import logging
        import traceback
        from contextlib import asynccontextmanager
        from pathlib import Path

        from fastapi import FastAPI, File, Form, HTTPException, UploadFile
        from fastapi.encoders import jsonable_encoder
        from fastapi.responses import JSONResponse
        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter
        from marker.settings import settings

        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        logger = logging.getLogger(__name__)

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info("Datalab Marker / Modal demo app starting up...")
            yield
            logger.info("Datalab Marker / Modal demo app shutting down...")

        web_app = FastAPI(
            title="Datalab Marker PDF Conversion Service - Modal Demo",
            description="Convert PDFs and documents to markdown, JSON, or HTML using Marker, deployed on Modal",
            version="1.0.0",
            lifespan=lifespan,
        )

        @web_app.get("/health")
        async def health_check():
            models_loaded = hasattr(self, "models") and self.models is not None
            model_count = len(self.models) if models_loaded else 0

            cache_exists = os.path.exists(MODEL_PATH_PREFIX)
            cache_contents = os.listdir(MODEL_PATH_PREFIX) if cache_exists else []

            return {
                "status": "healthy" if models_loaded else "loading",
                "models_loaded": models_loaded,
                "model_count": model_count,
                "cache_dir": MODEL_PATH_PREFIX,
                "cache_exists": cache_exists,
                "cache_contents": cache_contents[:10],
            }

        @web_app.post("/convert")
        async def convert_document(
            file: UploadFile = File(..., description="Document to convert"),
            page_range: Optional[str] = Form(None),
            force_ocr: bool = Form(False),
            paginate_output: bool = Form(False),
            output_format: str = Form("markdown"),
            use_llm: bool = Form(False),
        ):
            """Convert uploaded document to specified format."""
            if not hasattr(self, "models") or self.models is None:
                logger.error("Models not available for conversion")
                raise HTTPException(
                    status_code=503, detail="Models not loaded yet. Please wait for model initialization."
                )

            allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400, detail=f"Unsupported file type: {file_ext}. Supported: {allowed_extensions}"
                )

            if output_format not in ["markdown", "json", "html", "chunks"]:
                raise HTTPException(
                    status_code=400, detail="Output format must be one of: markdown, json, html, chunks"
                )

            try:
                # Read and save file
                file_content = await file.read()
                temp_path = f"/tmp/{file.filename}"
                with open(temp_path, "wb") as temp_file:
                    temp_file.write(file_content)

                # Configure conversion parameters
                config = {
                    "filepath": temp_path,
                    "page_range": page_range,
                    "force_ocr": force_ocr,
                    "paginate_output": paginate_output,
                    "output_format": output_format,
                    "use_llm": use_llm,
                }

                # Create converter
                config_parser = ConfigParser(config)
                config_dict = config_parser.generate_config_dict()
                config_dict["pdftext_workers"] = 1

                converter = PdfConverter(
                    config=config_dict,
                    artifact_dict=self.models,
                    processor_list=config_parser.get_processors(),
                    renderer=config_parser.get_renderer(),
                    llm_service=config_parser.get_llm_service() if use_llm else None,
                )

                logger.info(f"Converting {file.filename} to {output_format}...")
                rendered_output = converter(temp_path)

                # Prepare response payload
                json_content = None
                html_content = None
                markdown_content = None
                encoded_images = {}

                if output_format == "json":
                    # Robust Pydantic serialization
                    try:
                        json_content = rendered_output.model_dump(mode="json")
                    except Exception as e:
                        logger.warning(f"model_dump(mode='json') failed ({e}); trying model_dump_json.")
                        import json as pyjson

                        json_content = pyjson.loads(rendered_output.model_dump_json())
                else:
                    from marker.output import text_from_rendered

                    text, _, images = text_from_rendered(rendered_output)

                    if output_format == "html":
                        html_content = text
                    else:
                        markdown_content = text

                    for img_name, img_obj in images.items():
                        byte_stream = io.BytesIO()
                        img_obj.save(byte_stream, format=settings.OUTPUT_IMAGE_FORMAT)
                        encoded_images[img_name] = base64.b64encode(byte_stream.getvalue()).decode("utf-8")

                metadata = jsonable_encoder(getattr(rendered_output, "metadata", {}))

                logger.info(f"Conversion completed for {file.filename}")
                os.unlink(temp_path)

                payload = {
                    "success": True,
                    "filename": file.filename,
                    "output_format": output_format,
                    "json": json_content,
                    "html": html_content,
                    "markdown": markdown_content,
                    "images": encoded_images,
                    "metadata": metadata,
                    "page_count": len(metadata.get("page_stats", [])) if isinstance(metadata, dict) else None,
                }
                return JSONResponse(content=jsonable_encoder(payload))

            except Exception as e:
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception:
                    pass

                logger.error(f"Conversion error for {file.filename}: {e!s}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Conversion failed: {e!s}")

        return web_app
