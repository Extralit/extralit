import itertools
import logging
from datetime import datetime
from typing import Dict, Iterator, Tuple, Optional, Union
from uuid import UUID

import pandas as pd
import pandera as pa
from pandera.api.base.model import MetaModel
from pydantic.v1 import BaseModel, Field

from extralit.extraction.models.schema import SchemaStructure

_LOGGER = logging.getLogger(__name__)


class PaperExtraction(BaseModel):
    reference: str
    extractions: Dict[str, pd.DataFrame] = Field(default_factory=dict)
    schemas: SchemaStructure = Field(..., description="The schema structure of the extraction.")
    durations: Dict[str, Optional[float]] = Field(default_factory=dict)
    updated_at: Dict[str, Optional[datetime]] = Field(default_factory=dict)
    inserted_at: Dict[str, Optional[datetime]] = Field(default_factory=dict)
    user_id: Dict[str, Optional[UUID]] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def get_joined_data(self, schema_name: str, drop_joined_index=True) -> pd.DataFrame:
        """
        Join the extraction DataFrame with the dependent DataFrames based on the schema index.
        Args:
            schema_name:  The schema name to join.
            drop_joined_index:  Drop the joined index column.
            index_name: The index name to join on.

        Returns:

        """
        schema = self.schemas[schema_name]
        df = self[schema_name].copy()

        # For each '_ref' key, find the matching DataFrame with the same DataFrameModel prefix
        for ref_column in self.schemas.index_names(schema_name):
            dep_schema_name = self.schemas.get_ref_schema(ref_column).name
            if ref_column not in df.index.names and ref_column not in df.columns:
                # Skip if the DataFrame is already joined
                _LOGGER.info(f"Skipping join on {ref_column} as it is already joined. \n{df.index.names}\n{df.columns}")
                continue

            dependent_df = next(
                (value.copy() for key, value in self.extractions.items() \
                 if str(key).lower() == dep_schema_name.lower() and value.size > 0),
                None)
            if dependent_df is None:
                continue

            if self.user_id.get(dep_schema_name) and self.user_id.get(dep_schema_name) == self.user_id.get(schema_name):
                print(f"Skipping join on {dep_schema_name} as it is the same user.")
                _LOGGER.info(f"Skipping join on {dep_schema_name} as it is the same user.")

            try:
                dependent_df = dependent_df.rename_axis(index={'reference': ref_column})
                df = df.join(dependent_df, how='left', rsuffix='_joined')
                df = overwrite_joined_columns(df, rsuffix='_joined', prepend=True)
                if drop_joined_index and ref_column in df.index.names:
                    df = df.reset_index(level=ref_column, drop=True)
            except NotImplementedError as e:
                _LOGGER.info(f'{dep_schema_name}-{schema.name} extraction table is already joined.')
            except Exception as e:
                _LOGGER.error(f"Failed to join `{dep_schema_name}` to {schema.name}: {e}")
                raise e

        return df

    @property
    def size(self):
        return sum(df.size for schema_name, df in self.extractions.items())

    def __getitem__(self, item: str) -> pd.DataFrame:
        if isinstance(item, pa.DataFrameSchema):
            return self.extractions[item.name]
        elif isinstance(item, MetaModel):
            return self.extractions[str(item)]
        return self.extractions[item]

    def __contains__(self, item: Union[pa.DataFrameModel, str]) -> bool:
        if isinstance(item, pa.DataFrameSchema):
            return item.name in self.extractions
        elif isinstance(item, MetaModel):
            return str(item) in self.extractions
        return item in self.extractions

    def __getattr__(self, item: str) -> pd.DataFrame:
        if self.__contains__(item):
            return self.__getitem__(item)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    def __dir__(self) -> Iterator[str]:
        extraction_keys = [str(key) for key in self.extractions.keys()]
        return itertools.chain(super().__dir__(), extraction_keys)

    def __setitem__(self, key: str, value: pd.DataFrame) -> None:
        assert isinstance(key, str), f"Expected str, got {type(key)}"
        self.extractions[key] = value

    def items(self) -> Iterator[Tuple[str, pd.DataFrame]]:
        return self.extractions.items()

    def __repr_args__(self):
        args = [(k, v.dropna(axis=1, how='all').shape) for k, v in self.extractions.items() if v.size]
        return args


def overwrite_joined_columns(df: pd.DataFrame, rsuffix='_joined', prepend=True) -> pd.DataFrame:
    # Overwrite the original column with the '_joined' column
    suffix_columns = [col for col in df.columns if col.endswith(rsuffix)]
    joined_columns = [col.rsplit(rsuffix, 1)[0] for col in suffix_columns]

    for joined_col in suffix_columns:
        original_col = joined_col.rsplit(rsuffix, 1)[0]
        df[original_col] = df[joined_col]
        df = df.drop(columns=joined_col)

    if prepend:
        column_reorder = [*joined_columns, *df.columns.difference(joined_columns)]
        df = df.reindex(columns=column_reorder)

    return df
