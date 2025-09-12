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

import os
from typing import Optional

import typer

from extralit_server.integrations.huggingface.spaces import HUGGINGFACE_SETTINGS
from extralit_server.security.authentication.oauth2.extralit_hub import ExtralitHubOpenId


def register_instance(
    hub_url: Optional[str] = typer.Option(None, "--hub-url", help="Hub URL (default: auto-detect)"),
    force: bool = typer.Option(False, "--force", help="Force re-registration even if credentials exist"),
):
    """Register this instance with the Extralit Hub."""
    typer.echo("🔐 Registering instance with Extralit Hub...")

    try:
        # Initialize the Hub OIDC backend
        hub_backend = ExtralitHubOpenId()

        if hub_url:
            hub_backend._hub_base_url = hub_url.rstrip("/")
            hub_backend._setup_oidc_endpoints()

        # Check current status
        if not force and hub_backend._load_stored_credentials():
            typer.echo("✅ Instance already registered with Hub")
            typer.echo(f"   Client ID: {hub_backend._client_credentials['client_id']}")
            return

        # Force re-registration
        typer.echo("📋 Preparing registration data...")
        registration_data = hub_backend._prepare_registration_data()

        typer.echo(f"   Instance Name: {registration_data['instance_name']}")
        typer.echo(f"   Instance Type: {registration_data['instance_type']}")
        typer.echo(f"   Redirect URI: {registration_data['redirect_uris'][0]}")
        typer.echo(f"   Hub URL: {hub_backend._hub_base_url}")

        # Perform registration
        typer.echo("🚀 Registering with Hub...")
        hub_backend._register_with_hub()

        typer.echo("✅ Registration successful!")
        if hub_backend._client_credentials:
            typer.echo(f"   Client ID: {hub_backend._client_credentials['client_id']}")
            typer.echo("   Client secret has been stored securely")

    except Exception as e:
        typer.echo(f"❌ Registration failed: {e}")
        raise typer.Exit(1)


def check_status():
    """Check Hub authentication status."""
    typer.echo("🔍 Checking Hub authentication status...")

    try:
        hub_backend = ExtralitHubOpenId()

        typer.echo(f"   Hub URL: {hub_backend._hub_base_url}")

        if hub_backend._client_credentials:
            typer.echo("✅ Hub credentials found")
            typer.echo(f"   Client ID: {hub_backend._client_credentials['client_id']}")
            typer.echo("   Client secret: [CONFIGURED]")
        else:
            typer.echo("❌ No Hub credentials found")
            typer.echo("   Run 'pdm run cli hub-auth register' to register this instance")

        # Environment info
        if HUGGINGFACE_SETTINGS.is_running_on_huggingface:
            typer.echo("🤗 HuggingFace Spaces Environment:")
            typer.echo(f"   Space ID: {HUGGINGFACE_SETTINGS.space_id}")
            typer.echo(f"   Space Author: {HUGGINGFACE_SETTINGS.space_author_name}")
            typer.echo(f"   Space Repository: {HUGGINGFACE_SETTINGS.space_repo_name}")
        else:
            typer.echo("🏠 Self-hosted Environment")

    except Exception as e:
        typer.echo(f"❌ Status check failed: {e}")
        raise typer.Exit(1)


def test_oidc_flow():
    """Test OIDC configuration and endpoints."""
    typer.echo("🧪 Testing OIDC configuration...")

    try:
        hub_backend = ExtralitHubOpenId()

        if not hub_backend._client_credentials:
            typer.echo("❌ No credentials found. Register first with: pdm run cli hub-auth register")
            raise typer.Exit(1)

        typer.echo("✅ Credentials loaded")
        typer.echo(f"   Authorization URL: {hub_backend.AUTHORIZATION_URL}")
        typer.echo(f"   Token URL: {hub_backend.ACCESS_TOKEN_URL}")
        typer.echo(f"   OIDC Endpoint: {hub_backend.OIDC_ENDPOINT}")

        # Test redirect URI
        redirect_uri = hub_backend.get_redirect_uri()
        typer.echo(f"   Redirect URI: {redirect_uri}")

        typer.echo("✅ OIDC configuration appears valid")
        typer.echo("\n🔗 To test the flow:")

        if HUGGINGFACE_SETTINGS.is_running_on_huggingface:
            space_id = HUGGINGFACE_SETTINGS.space_id
            typer.echo(f"   1. Visit: https://{space_id}.hf.space/login")
            typer.echo("   2. Click 'Sign in with Extralit Hub'")
        else:
            typer.echo("   1. Visit your instance's login page")
            typer.echo("   2. Click 'Sign in with Extralit Hub'")

    except Exception as e:
        typer.echo(f"❌ OIDC test failed: {e}")
        raise typer.Exit(1)


def clear_credentials(force: bool = typer.Option(False, "--force", help="Skip confirmation prompt")):
    """Clear stored Hub credentials."""
    if not force:
        confirm = typer.confirm("Are you sure you want to clear stored credentials?")
        if not confirm:
            typer.echo("Operation cancelled.")
            raise typer.Exit(0)

    typer.echo("🗑️  Clearing stored credentials...")

    try:
        # Remove credentials file if it exists
        credentials_file = os.path.join(os.getcwd(), ".extralit_hub_credentials")
        if os.path.exists(credentials_file):
            os.remove(credentials_file)
            typer.echo(f"   Removed: {credentials_file}")

        typer.echo("✅ Credentials cleared")
        typer.echo("   You'll need to re-register with: pdm run cli hub-auth register")

    except Exception as e:
        typer.echo(f"❌ Failed to clear credentials: {e}")
        raise typer.Exit(1)
