

from typing import Dict, Optional

import typer

from argilla.client.enums import DatasetType
from extralit.server.context.files import get_minio_client

def export_data(
    ctx: typer.Context,
    type_: Optional[DatasetType] = typer.Option(
        None,
        "--type",
        help="The type of datasets to be listed. This option can be used multiple times. By default, all datasets are listed.",
    ),
) -> None:
    print("export_data", ctx.obj, type_)
    print(get_minio_client())
    