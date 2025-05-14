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

from typing import Optional, TYPE_CHECKING

import typer

from argilla.cli.callback import init_callback
from argilla.cli.rich import get_argilla_themed_panel
from argilla.cli.rich import print_rich_table
from rich.console import Console

if TYPE_CHECKING:
    pass


app = typer.Typer(help="Commands for dataset management", no_args_is_help=True)


@app.command(name="list", help="List datasets linked to user's workspaces")
def list_datasets(
    workspace: str = typer.Option(..., help="Filter datasets by workspace"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show minimal stack trace for debugging"),
) -> None:
    """List datasets with optional filtering by workspace and type."""
    try:
        client = init_callback()

        datasets = client.datasets(workspace=workspace)

        print_rich_table(resources=datasets, title="Datasets")
    except Exception as e:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to list datasets",
            title="Unexpected error",
            title_align="left",
            success=False,
            exception=e,
            debug=debug,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="delete", help="Deletes a dataset")
def delete_dataset(
    name: str = typer.Option(..., "--name", "-n", help="The name of the dataset to delete"),
    workspace: Optional[str] = typer.Option(None, help="The name of the workspace where the dataset belongs"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show minimal stack trace for debugging"),
) -> None:
    """Delete a dataset from the system."""
    try:
        client = init_callback()

        dataset = client.datasets(name=name, workspace=workspace)
        dataset.delete()

        panel = get_argilla_themed_panel(
            f"Dataset with name={dataset.name} and workspace={dataset.workspace.name} deleted successfully",
            title="Dataset deleted",
            title_align="left",
        )
        Console().print(panel)
    except RuntimeError as re:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to delete the dataset",
            title="Unexpected error",
            title_align="left",
            success=False,
            exception=re,
            debug=debug,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except Exception as e:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when fetching the dataset",
            title="Unexpected error",
            title_align="left",
            success=False,
            exception=e,
            debug=debug,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="push-to-huggingface", help="Push a dataset to HuggingFace Hub", hidden=True)
def push_to_huggingface(
    name: str = typer.Argument(..., help="The name of the dataset to push"),
    repo_id: str = typer.Option(..., help="The HuggingFace Hub repo where the dataset will be pushed to"),
    workspace: Optional[str] = typer.Option(None, help="The name of the workspace where the dataset belongs"),
    private: bool = typer.Option(False, help="Whether the dataset should be private or not"),
    token: Optional[str] = typer.Option(None, help="The HuggingFace Hub token to be used for pushing the dataset"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show minimal stack trace for debugging"),
) -> None:
    """Push a dataset to the HuggingFace Hub."""
    try:
        client = init_callback()

        try:
            dataset = client.datasets(name=name, workspace=workspace)
        except ValueError as e:
            panel = get_argilla_themed_panel(
                str(e),
                title="Dataset not found",
                title_align="left",
                success=False,
                exception=e,
                debug=debug,
            )
            Console().print(panel)
            raise typer.Exit(1)
        except Exception as e:
            panel = get_argilla_themed_panel(
                "An unexpected error occurred when fetching the dataset",
                title="Unexpected error",
                title_align="left",
                success=False,
                exception=e,
                debug=debug,
            )
            Console().print(panel)
            raise typer.Exit(code=1)

        from rich.live import Live
        from rich.spinner import Spinner

        spinner = Spinner(
            name="dots",
            text=f"Pushing dataset with name={dataset.name} and workspace={dataset.workspace.name} to the"
            " HuggingFace Hub...",
        )

        with Live(spinner, refresh_per_second=20):
            client.push_dataset_to_huggingface(
                name=dataset.name, repo_id=repo_id, private=private, token=token, workspace=dataset.workspace
            )

        panel = get_argilla_themed_panel(
            f"Dataset successfully pushed to the HuggingFace Hub at https://huggingface.co/{repo_id}",
            title="Dataset pushed",
            title_align="left",
        )
        Console().print(panel)
    except ValueError as ve:
        panel = get_argilla_themed_panel(
            "The dataset has no records to push to the HuggingFace Hub. Make sure to add records before" " pushing it.",
            title="No records to push",
            title_align="left",
            success=False,
            exception=ve,
            debug=debug,
        )
        Console().print(panel)
        raise typer.Exit(1)
    except Exception as e:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to push the dataset to the HuggingFace Hub",
            title="Unexpected error",
            title_align="left",
            success=False,
            exception=e,
            debug=debug,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="create", help="Creates a new dataset with configurable settings", hidden=True)
def create_dataset(
    name: str = typer.Option(..., prompt=True, help="The name of the dataset to be created"),
    workspace: str = typer.Option(
        ...,
        prompt=True,
        help="The workspace where the dataset will be created",
    ),
    guidelines: Optional[str] = typer.Option(None, prompt=True, help="Guidelines for annotators (optional)"),
    allow_extra_metadata: bool = typer.Option(False, prompt=True, help="Whether to allow extra metadata in records"),
    advanced_config: bool = typer.Option(False, prompt=True, help="Configure fields and questions interactively"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show minimal stack trace for debugging"),
) -> None:
    """Create a new dataset with configurable settings in the system."""
    try:
        client = init_callback()

        from argilla.settings import Settings, TextField, TextQuestion
        from argilla.datasets._resource import Dataset

        fields = [TextField(name="text", title="Text")]
        questions = [TextQuestion(name="comment", title="Comment", description="Add your comments here")]

        if advanced_config:
            if typer.confirm("Add a text field?", default=True):
                field_name = typer.prompt("Field name", default="text")
                field_title = typer.prompt("Field title", default="Text")
                fields = [TextField(name=field_name, title=field_title)]

            if typer.confirm("Add a text question?", default=True):
                question_name = typer.prompt("Question name", default="comment")
                question_title = typer.prompt("Question title", default="Comment")
                question_desc = typer.prompt("Question description", default="Add your comments here")
                questions = [TextQuestion(name=question_name, title=question_title, description=question_desc)]

        settings = Settings(
            fields=fields, questions=questions, guidelines=guidelines, allow_extra_metadata=allow_extra_metadata
        )

        dataset = Dataset(name=name, workspace=workspace, settings=settings, client=client)
        dataset.create()

        panel = get_argilla_themed_panel(
            f"Dataset with name='{name}' successfully created in workspace='{workspace}'.",
            title="Dataset created",
            title_align="left",
        )
        Console().print(panel)
    except ValueError as ve:
        panel = get_argilla_themed_panel(
            "Dataset creation failed",
            title="Dataset creation failed",
            title_align="left",
            success=False,
            exception=ve,
            debug=debug,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except RuntimeError as re:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to create the dataset",
            title="Unexpected error",
            title_align="left",
            success=False,
            exception=re,
            debug=debug,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except Exception as e:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to create the dataset",
            title="Unexpected error",
            title_align="left",
            success=False,
            exception=e,
            debug=debug,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
