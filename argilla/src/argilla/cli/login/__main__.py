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

from typing import Optional

import typer

app = typer.Typer(invoke_without_command=True)


def login_impl(api_url: str, api_key: str, workspace: Optional[str] = None, extra_headers: Optional[dict] = None):
    """
    Implementation of the login functionality.
    
    In a full implementation, this would use the v2 API client.
    For now we'll implement a simple placeholder that just stores credentials.
    """
    import os
    import json
    from pathlib import Path
    
    # Create argilla directory if it doesn't exist
    argilla_dir = Path.home() / ".argilla"
    argilla_dir.mkdir(exist_ok=True)
    
    # Create credentials file
    credentials = {
        "api_url": api_url,
        "api_key": api_key,
    }
    
    if workspace:
        credentials["workspace"] = workspace
        
    if extra_headers:
        credentials["extra_headers"] = extra_headers
    
    # Write credentials to file
    with open(argilla_dir / "credentials.json", "w") as f:
        json.dump(credentials, f)
    
    # For debug/development only - will be removed in full implementation
    return True


@app.callback(help="Login to an Extralit Server")
def login(
    api_url: str = typer.Option(..., prompt="API URL", help="The URL of the Extralit Server to login in to"),
    api_key: str = typer.Option(
        ..., prompt="API Key", hide_input=True, help="The API key for logging into the Extralit Server"
    ),
    workspace: Optional[str] = typer.Option(
        None, help="The default workspace over which the operations will be performed"
    ),
    extra_headers: Optional[str] = typer.Option(
        None, help="A JSON string with extra headers to be sent in the requests to the Extralit Server"
    ),
):
    """Login to an Extralit Server by providing API URL and API key credentials."""
    import json

    from argilla.cli.rich import get_argilla_themed_panel
    from rich.console import Console

    try:
        headers = {}
        if extra_headers:
            headers = json.loads(extra_headers)
            
        # Call the implementation function
        login_impl(api_url=api_url, api_key=api_key, workspace=workspace, extra_headers=headers)
        
    except json.JSONDecodeError:
        panel = get_argilla_themed_panel(
            "The provided extra headers are not a valid JSON string.",
            title="Extra headers error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except ValueError as e:
        panel = get_argilla_themed_panel(
            f"Could not login to the '{api_url}' Extralit server. Please check the provided credentials and try again.",
            title="Login error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1) from e

    panel = get_argilla_themed_panel(
        f"Logged in successfully to '{api_url}' Extralit server!", 
        title="Logged in", 
        title_align="left"
    )
    Console().print(panel)


if __name__ == "__main__":
    app()