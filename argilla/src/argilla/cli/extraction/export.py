

from typing import Dict, Optional

import typer

from argilla.client.enums import DatasetType
from 

def export_data(
    workspace: Optional[str] = typer.Option(None, help="Filter datasets by workspace"),
    type_: Optional[DatasetType] = typer.Option(
        None,
        "--type",
        help="The type of datasets to be listed. This option can be used multiple times. By default, all datasets are listed.",
    ),
) -> None:
    print("export_data", workspace, type_)
    