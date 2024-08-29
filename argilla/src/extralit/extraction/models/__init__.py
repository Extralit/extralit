from .schema import SchemaStructure, DEFAULT_SCHEMA_S3_PATH
from .response import ResponseResults
from .paper import PaperExtraction

from extralit.schema.checks import register_check_methods
register_check_methods()
