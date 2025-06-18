import os
from typing import Dict

import pandera as pa
from pandera.io import from_yaml


def load_schemas(dir_path: str) -> Dict[str, pa.DataFrameSchema]:
    dataframe_models = {}
    for filename in os.listdir(dir_path):
        if not filename.endswith('.yaml') or not os.path.exists(os.path.join(dir_path, filename)):
            continue

        schema: pa.DataFrameSchema = from_yaml(os.path.join(dir_path, filename))
        dataframe_models[schema.name] = schema

    return dataframe_models
