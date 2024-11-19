import logging
from typing import List, Optional, Type, Union, Dict, Any

import pandas as pd
import pandera as pa
from pydantic.v1 import BaseModel, Field, create_model

from extralit.extraction.utils import stringify_lists
from extralit.extraction.staging import heal_json, to_df


class SchemaStructuredOutputResponseModel(BaseModel):

    @classmethod
    def parse_raw(cls, b, **kwargs):
        healed_json_string = heal_json(b)
        try:
            output = super().parse_raw(healed_json_string, **kwargs)
        except Exception as e:
            logging.error(f'Error parsing {cls.__name__}: {e}\n'
                          f'Given: "{healed_json_string}"')
            return cls(items=[])

        return output

    def to_df(self, *args, **kwargs) -> pd.DataFrame:
        return to_df(self, *args, **kwargs)

    class Config:
        validate_assignment = False
        arbitrary_types_allowed = True


def clean_docstring(description: str) -> Optional[str]:
    if description is None:
        return None

    cleaned_description = description.strip().replace('\n', ' ')
    return cleaned_description


def pandera_dtype_to_python_type(pandera_dtype: Type[pa.typing.Series]) -> Type:
    if isinstance(pandera_dtype, pa.DataType):
        dtype = pandera_dtype.type

        if dtype == 'int':
            return Optional[Union[int, str]]
        elif dtype == 'float':
            return Optional[Union[float, str]]
        elif dtype == list:
            return Optional[List[str]]
        elif dtype == bool:
            return Optional[bool]
        elif dtype in ['O', 'S', 'U']:
            return Optional[str]

    return Optional[str]


def pandera_column_to_pydantic_field(column: pa.Column, validate_assignment=False, description_only=False) -> Field:
    description = column.description or ""

    if description_only:
        return Field(None, title=column.title, description=description)

    if column.checks:
        description += "\nSpecifications:"

    validators = {}
    extra = {}

    for check in column.checks:
        if 'greater_than_or_equal_to' == check.name:
            validators['ge'] = check.statistics['min_value']
            if not validate_assignment:
                description += f"\n{check.name}: {next(iter(check.statistics.values()), None)}"
        elif 'less_than_or_equal_to' == check.name:
            validators['le'] = check.statistics['max_value']
            if not validate_assignment:
                description += f"\n{check.name}: {next(iter(check.statistics.values()), None)}"
        elif 'less_than' == check.name:
            validators['lt'] = check.statistics['max_value']
            if not validate_assignment:
                description += f"\n{check.name}: {next(iter(check.statistics.values()), None)}"
        elif 'greater_than' == check.name:
            validators['gt'] = check.statistics['min_value']
            if not validate_assignment:
                description += f"\n{check.name}: {next(iter(check.statistics.values()), None)}"

        elif 'str_matches' == check.name:
            validators['regex'] = check.statistics['pattern']
            if not validate_assignment:
                extra['str_matches'] = check.statistics['pattern']
        elif 'str_length' == check.name and 'min_value' in check.statistics:
            validators['min_length'] = check.statistics['min_value']
            if not validate_assignment:
                extra.setdefault('str_length', {})['min_value'] = check.statistics['min_value']
        elif 'str_length' == check.name and 'max_value' in check.statistics:
            validators['max_length'] = check.statistics['max_value']
            if not validate_assignment:
                extra.setdefault('str_length', {})['max_value'] = check.statistics['max_value']

        elif 'str_startswith' == check.name or 'str_endswith' == check.name:
            description += f'\n{check.name}: "{check.statistics["string"]}"'

        elif 'suggestion' == check.name:
            # description += f"\nSuggestion: {stringify_to_instructions(check.statistics['values'])}"
            extra['suggestion'] = check.statistics['values']
        elif 'isin' == check.name:
            description += f"\nAllowed values: {stringify_lists(check.statistics['allowed_values'])}"
            extra['allowed_values'] = check.statistics['allowed_values']
        elif 'notin' == check.name:
            description += f"\nForbidden values: {stringify_lists(check.statistics['forbidden_values'])}"
            extra['forbidden_values'] = check.statistics['forbidden_values']

        elif check.name == "multiselect":
            description += f'\nmultivalues: "{check.statistics["delimiter"]}" delimited'

        else:
            description += f"\n{check.name}: {check.statistics}"

    if description.endswith("\nSpecifications:"):
        description = description.replace("\nSpecifications:", "")

    if not validate_assignment:
        return Field(None, title=column.title, description=description,
                     **(dict(json_schema_extra=extra) if extra else {}))

    return Field(None, title=column.title, description=description, **validators,
                 **(dict(json_schema_extra=extra) if extra else {}))


def get_extraction_schema_model(
        schema: pa.DataFrameSchema,
        include_fields: List[str]=None,
        exclude_fields: List[str]=None,
        top_class: Optional[str] = None,
        lower_class: Optional[str] = None,
        singleton=False,
        validate_assignment=False,
        description_only=False,) -> Type[SchemaStructuredOutputResponseModel]:
    """
    Converts a Pandera DataFrameSchema to a Pydantic model. This model encodes checks and dtypes which will be used as a
    prompt to guide an LLM's JSON output. The function dynamically creates Pydantic models with fields based on the
    schema columns and index. If the schema is not a singleton, it creates a lower-level model for each row and a
    top-level model that contains a list of the lower-level models. If the schema is a singleton, it creates a single
    top-level model.

    Args:
        schema (pa.DataFrameSchema): The Pandera DataFrameSchema to convert.
        include_fields (List[str], optional): A list of column names to include in the Pydantic model. Defaults to None.
        exclude_fields (List[str], optional): A list of column names to exclude in the Pydantic model. Defaults to None.
        top_class (str, optional): The name of the top-level Pydantic model. Defaults to a plural form of the schema name.
        lower_class (str, optional): The name of the lower-level Pydantic model. Defaults to the schema name.
        singleton (bool, optional): Whether the schema represents a singleton. Defaults to False.
            When True, the top-level model will not contain a list of lower-level model and only contain a single
            value for each field.
        validate_assignment: Whether to enforce validators on the LLM extractions, and potentially raising Exceptions.
            Defaults to False.
        description_only: Whether to include only the description in the Pydantic model.
            Defaults to False.

    Returns:
        Type[SchemaStructuredOutputResponseModel]: The Pydantic model that represents the schema definition and constraints.
    """
    assert isinstance(schema, pa.DataFrameSchema), f"Expected DataFrameSchema, got {type(schema)}"
    if top_class is None:
        top_class = schema.name + ('s' if not singleton else '')
    if lower_class is None:
        lower_class = schema.name

    # Dynamically create fields for the lower-level model based on schema columns
    columns = {
        field_name: (
            pandera_dtype_to_python_type(column.dtype),
            pandera_column_to_pydantic_field(
                column, validate_assignment=validate_assignment, description_only=description_only)
        )
        for field_name, column in schema.columns.items() \
        if not include_fields or field_name in include_fields
    }
    for field_name in include_fields or []:
        if field_name not in columns:
            columns[field_name] = (Optional[str], Field(None, title=field_name))

    # Add fields from schema.index
    index_fields = (schema.index.indexes if hasattr(schema.index, 'indexes') else [schema.index])
    indexes = {
        index.name: (
            pandera_dtype_to_python_type(index.dtype),
            pandera_column_to_pydantic_field(
                index, validate_assignment=validate_assignment)
        )
        for index in index_fields \
        if (index and index.name)
    }
    if exclude_fields:
        columns = {k: v for k, v in columns.items() if k not in exclude_fields}
        indexes = {k: v for k, v in indexes.items() if k not in exclude_fields}

    if not singleton:
        lower_level_model = create_model(
            __model_name=lower_class,
            **indexes,
            **columns
        )
        top_level_model = create_model(
            __model_name=top_class,
            __base__=SchemaStructuredOutputResponseModel,
            items=(List[lower_level_model],
                   Field(default_factory=list)),
        )

    else:
        top_level_model = create_model(
            __model_name=top_class,
            __base__=SchemaStructuredOutputResponseModel,
            **indexes, **columns
        )

    top_level_model.__doc__ = clean_docstring(schema.description)

    return top_level_model


def drop_type_def_from_schema_json(schema_json: Dict[str, Any]) -> Dict[str, Any]:

    for key in schema_json.get('properties', []):
        schema_json['properties'][key].pop('type', None)
        schema_json['properties'][key].pop('anyOf', None)
    for definition in schema_json.get('definitions', {}).values():
        for key in definition.get('properties', {}):
            definition['properties'][key].pop('type', None)
            definition['properties'][key].pop('anyOf', None)

    return schema_json
