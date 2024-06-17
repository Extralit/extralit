import logging
import os
from collections import deque
from glob import glob
from io import BytesIO
from typing import List, Optional, Union, Dict

import pandera as pa
from minio import Minio
from pandera.api.base.model import MetaModel
from pandera.io import from_json, from_yaml
from pydantic.v1 import BaseModel, Field, validator

_LOGGER = logging.getLogger(__name__)

class SchemaStructure(BaseModel):
    schemas: List[pa.DataFrameSchema] = Field(default_factory=list)
    document_schema: Optional[pa.DataFrameSchema] = None

    @validator('schemas', pre=True, each_item=True)
    def parse_schema(cls, v: Union[pa.DataFrameModel, pa.DataFrameSchema]):
        return v.to_schema() if hasattr(v, 'to_schema') else v

    @validator('document_schema', pre=True)
    def parse_document_schema(cls, v: Union[pa.DataFrameModel, pa.DataFrameSchema]):
        schema: pa.DataFrameSchema = v.to_schema() if hasattr(v, 'to_schema') else v
        assert all(key.islower() for key in schema.columns.keys()), f"All keys in {schema.name} schema must be lowercased"
        return schema

    @classmethod
    def from_dir(cls, dir_path: str, exclude: List[str]=[]):
        schemas = {}
        if os.path.isdir(dir_path):
            schema_paths = sorted(glob(os.path.join(dir_path, '*.json')), key=lambda x: not x.endswith('.json'))
        else:
            schema_paths = sorted(glob(dir_path), key=lambda x: not x.endswith('.json'))

        for filepath in schema_paths:
            try:
                if filepath.endswith('.json'):
                    schema = from_json(filepath)
                elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                    schema = from_yaml(filepath)
                else:
                    continue

                if schema.name in schemas or schema.name in exclude:
                    continue

                schemas[schema.name] = schema
            except Exception as e:
                _LOGGER.warning(f"Ignoring failed schema loading from '{filepath}': \n{e}")

        return cls(schemas=list(schemas.values()))

    @classmethod
    def from_s3(cls, workspace: str, minio_client: Minio, prefix: str = 'schemas/',
                exclude: List[str] = [], verbose: bool = True):
        schemas = {}
        objects = minio_client.list_objects(workspace, prefix=prefix, include_version=False)

        # Sort the objects by file extension
        objects = sorted(objects, key=lambda obj: (
            os.path.splitext(obj.object_name)[1] != '', os.path.splitext(obj.object_name)[1]))

        for obj in objects:
            filepath = obj.object_name
            file_extension = os.path.splitext(filepath)[1]

            try:
                data = minio_client.get_object(workspace, filepath)
                file_data = BytesIO(data.read())

                if not file_extension or file_extension == '.json':
                    schema = from_json(file_data)
                elif file_extension in ['.yaml', '.yml']:
                    schema = from_yaml(file_data)
                else:
                    continue

                if schema.name in schemas or schema.name in exclude:
                    continue

                _LOGGER.info(f'Loaded {schema.name} from {filepath}', exc_info=1)
                print(f'Loaded {schema.name} from `{filepath}` in `{workspace}` bucket')
                schemas[schema.name] = schema
            except Exception as e:
                _LOGGER.warning(f"Ignoring failed schema loading from '{filepath}': \n{e}")

        return cls(schemas=list(schemas.values()))

    def to_s3(self, workspace: str, minio_client: Minio, prefix: str = 'schemas/'):
        for schema in self.schemas:
            # Serialize the schema to a JSON string
            schema_json = schema.to_json()

            # Create a BytesIO object from the JSON string
            schema_bytes = BytesIO(schema_json.encode())

            # Define the object name
            object_name = os.path.join(prefix, schema.name)

            # Upload the BytesIO object to the S3 bucket
            minio_client.put_object(
                bucket_name=workspace,
                object_name=object_name,
                data=schema_bytes,
                length=schema_bytes.getbuffer().nbytes,
                content_type='application/json'
            )

    def get_joined_schema(self, schema_name: str):
        combined_columns = {}
        combined_checks = []

        # Iterate over the provided schema and its dependent schemas
        dependent_schemas: List[pa.DataFrameSchema] = [
            self.__getitem__(sn) for sn in self.upstream_dependencies.get(schema_name)
        ]

        for schema in [self.__getitem__(schema_name)] + dependent_schemas:
            for column_name, column_schema in schema.columns.items():
                if column_name not in combined_columns:
                    combined_columns[column_name] = column_schema

            combined_checks.extend(schema.checks)

        joined_schema = pa.DataFrameSchema(columns=combined_columns, checks=combined_checks, name=schema_name)
        return joined_schema

    @property
    def downstream_dependencies(self) -> Dict[str, List[str]]:
        dependencies = {}
        for schema in self.schemas:
            dependencies[schema.name] = [dep.name for dep in self.schemas \
                                         if f"{schema.name}_ref".lower() in dep.index.names]
        return dependencies

    @property
    def upstream_dependencies(self) -> Dict[str, List[str]]:
        dependencies = {}
        for schema in self.schemas:
            dependencies[schema.name] = [
                other.name for other in self.schemas \
                if f"{other.name}_ref".lower() in (schema.index.names or [schema.index.name])]

        return dependencies

    def index_names(self, schema: str) -> List[str]:
        return list(self.__getitem__(schema).index.names or [self.__getitem__(schema).index.name])

    def columns(self, schema: str) -> List[str]:
        columns = list(self.__getitem__(schema).columns)
        return columns

    @property
    def ordering(self) -> List[str]:
        visited = {schema.name: 0 for schema in self.schemas}
        stack = deque()

        for schema in self.schemas:
            if visited[schema.name] == 0:
                # If the node is white, visit it
                topological_sort(schema.name, visited, stack, self.downstream_dependencies)

        return list(stack)

    def __iter__(self):
        return iter(self.ordering)

    def __getitem__(self, item: str):
        if isinstance(item, pa.DataFrameSchema):
            item = item.name
        elif isinstance(item, MetaModel):
            item = str(item)

        for schema in self.schemas:
            if schema.name.lower() == item.lower():
                return schema
        raise KeyError(f"No schema found for '{item}'")

    def __repr_args__(self):
        args = [(s.name, (s.index.names or [s.index.name]) + list(s.columns)) for s in self.schemas]
        return args

    class Config:
        arbitrary_types_allowed = True


def topological_sort(schema_name: str, visited: Dict[str, int], stack: deque,
                     dependencies: Dict[str, List[str]]) -> None:
    visited[schema_name] = 1  # Gray

    for i in dependencies.get(schema_name, []):
        if visited[i] == 1:  # If the node is gray, it means we have a cycle
            raise ValueError(f"Circular dependency detected: {schema_name} depends on {i} and vice versa")
        if visited[i] == 0:  # If the node is white, visit it
            topological_sort(i, visited, stack, dependencies)

    visited[schema_name] = 2  # Black
    stack.appendleft(schema_name)
