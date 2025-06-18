# Copyright 2024-present, Argilla, Inc.
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

from enum import Enum
import json
import typer

from argilla.cli.callback import init_callback
from argilla.cli.rich import get_argilla_themed_panel
from rich.console import Console


class Framework(str, Enum):
    """ML frameworks supported for training."""
    SPACY = "spacy"
    TRANSFORMERS = "transformers"
    SETFIT = "setfit"
    PEFT = "peft"


app = typer.Typer(no_args_is_help=True)


def framework_callback(value: str):
    """Validate and convert framework string to enum."""
    try:
        return Framework(value.lower())
    except ValueError:
        raise typer.BadParameter(
            f"Invalid framework {value}. Choose from {', '.join([f.value for f in Framework])}"
        )


# using callback to ensure it is used as sole command
@app.callback(help="Starts the Extralit Trainer", invoke_without_command=True)
def train(
    name: str = typer.Option(default=None, help="The name of the dataset to be used for training."),
    framework: Framework = typer.Option(
        default=None,
        callback=framework_callback,
        help="The framework to be used for training."
    ),
    workspace: str = typer.Option(default=None, help="The workspace to be used for training."),
    limit: int = typer.Option(default=None, help="The number of record to be used."),
    query: str = typer.Option(default=None, help="The query to be used."),
    model: str = typer.Option(default=None, help="The modelname or path to be used for training."),
    train_size: float = typer.Option(default=1.0, help="The train split to be used."),
    seed: int = typer.Option(default=42, help="The random seed number."),
    device: int = typer.Option(default=-1, help="The GPU id to be used for training."),
    output_dir: str = typer.Option(default="model", help="Output directory for the saved model."),
    update_config_kwargs: str = typer.Option(default="{}", help="update_config() kwargs to be passed as a dictionary."),
):
    """Start training a model using Extralit datasets."""
    init_callback()

    try:
        # Parse the JSON configuration
        try:
            config_kwargs = json.loads(update_config_kwargs)
        except json.JSONDecodeError:
            panel = get_argilla_themed_panel(
                "Invalid JSON format for update_config_kwargs.",
                title="Invalid configuration",
                title_align="left",
                success=False,
            )
            Console().print(panel)
            raise typer.Exit(code=1)

        # Initialize the client
        client = init_callback()

        # Display training configuration
        panel = get_argilla_themed_panel(
            f"Starting model training with:\n"
            f"- Dataset: {name or 'Not specified'} (workspace: {workspace or 'default'})\n"
            f"- Framework: {framework.value if framework else 'Not specified'}\n"
            f"- Model: {model or 'Default model'}\n"
            f"- Records: {limit or 'All'} (query: {query or 'None'})\n"
            f"- Training parameters: train_size={train_size}, seed={seed}, device={device}\n"
            f"- Output directory: {output_dir}",
            title="Training Started",
            title_align="left",
        )
        Console().print(panel)

        # Start training process with a spinner
        from rich.spinner import Spinner
        from rich.live import Live

        spinner = Spinner(
            name="dots",
            text="Training in progress...",
        )

        with Live(spinner, refresh_per_second=20):
            # Call the actual training function
            result = client.train_model(
                name=name,
                framework=framework.value,
                workspace=workspace,
                limit=limit,
                query=query,
                model=model,
                train_size=train_size,
                seed=seed,
                device=device,
                output_dir=output_dir,
                config_kwargs=config_kwargs
            )

        # Display training results
        metrics_str = "\n".join([f"- {k}: {v}" for k, v in result.get("metrics", {}).items()])
        panel = get_argilla_themed_panel(
            f"Model trained successfully and saved to {result['model_path']}\n"
            f"Metrics:\n{metrics_str if metrics_str else '- No metrics available'}",
            title="Training Complete",
            title_align="left",
        )
        Console().print(panel)

    except ValueError as e:
        panel = get_argilla_themed_panel(
            str(e),
            title="Invalid parameters",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)

    except Exception as e:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred during training.",
            title="Training Failed",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()