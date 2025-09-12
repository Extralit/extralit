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

import json
import os

import click

from extralit_server.integrations.huggingface.spaces import HUGGINGFACE_SETTINGS
from extralit_server.security.authentication.oauth2.extralit_hub import ExtralitHubOpenId


@click.group("hub-auth")
def hub_auth_cli():
    """Extralit Hub authentication management commands."""
    pass


@hub_auth_cli.command("register")
@click.option("--hub-url", help="Hub URL (default: auto-detect)")
@click.option("--force", is_flag=True, help="Force re-registration even if credentials exist")
def register_instance(hub_url: str, force: bool):
    """Register this instance with the Extralit Hub."""
    click.echo("🔐 Registering instance with Extralit Hub...")
    
    try:
        # Initialize the Hub OIDC backend
        hub_backend = ExtralitHubOpenId()
        
        if hub_url:
            hub_backend._hub_base_url = hub_url.rstrip('/')
            hub_backend._setup_oidc_endpoints()
        
        # Check current status
        if not force and hub_backend._load_stored_credentials():
            click.echo("✅ Instance already registered with Hub")
            click.echo(f"   Client ID: {hub_backend._client_credentials['client_id']}")
            return
        
        # Force re-registration
        click.echo("📋 Preparing registration data...")
        registration_data = hub_backend._prepare_registration_data()
        
        click.echo(f"   Instance Name: {registration_data['instance_name']}")
        click.echo(f"   Instance Type: {registration_data['instance_type']}")
        click.echo(f"   Redirect URI: {registration_data['redirect_uris'][0]}")
        click.echo(f"   Hub URL: {hub_backend._hub_base_url}")
        
        # Perform registration
        click.echo("🚀 Registering with Hub...")
        hub_backend._register_with_hub()
        
        click.echo("✅ Registration successful!")
        if hub_backend._client_credentials:
            click.echo(f"   Client ID: {hub_backend._client_credentials['client_id']}")
            click.echo("   Client secret has been stored securely")
        
    except Exception as e:
        click.echo(f"❌ Registration failed: {e}")
        exit(1)


@hub_auth_cli.command("status")
def check_status():
    """Check Hub authentication status."""
    click.echo("🔍 Checking Hub authentication status...")
    
    try:
        hub_backend = ExtralitHubOpenId()
        
        click.echo(f"   Hub URL: {hub_backend._hub_base_url}")
        
        if hub_backend._client_credentials:
            click.echo("✅ Hub credentials found")
            click.echo(f"   Client ID: {hub_backend._client_credentials['client_id']}")
            click.echo("   Client secret: [CONFIGURED]")
        else:
            click.echo("❌ No Hub credentials found")
            click.echo("   Run 'pdm run cli hub-auth register' to register this instance")
        
        # Environment info
        if HUGGINGFACE_SETTINGS.is_running_on_huggingface:
            click.echo("🤗 HuggingFace Spaces Environment:")
            click.echo(f"   Space ID: {HUGGINGFACE_SETTINGS.space_id}")
            click.echo(f"   Space Author: {HUGGINGFACE_SETTINGS.space_author_name}")
            click.echo(f"   Space Repository: {HUGGINGFACE_SETTINGS.space_repo_name}")
        else:
            click.echo("🏠 Self-hosted Environment")
            
    except Exception as e:
        click.echo(f"❌ Status check failed: {e}")
        exit(1)


@hub_auth_cli.command("test-oidc")
def test_oidc_flow():
    """Test OIDC configuration and endpoints."""
    click.echo("🧪 Testing OIDC configuration...")
    
    try:
        hub_backend = ExtralitHubOpenId()
        
        if not hub_backend._client_credentials:
            click.echo("❌ No credentials found. Register first with: pdm run cli hub-auth register")
            exit(1)
        
        click.echo("✅ Credentials loaded")
        click.echo(f"   Authorization URL: {hub_backend.AUTHORIZATION_URL}")
        click.echo(f"   Token URL: {hub_backend.ACCESS_TOKEN_URL}")
        click.echo(f"   OIDC Endpoint: {hub_backend.OIDC_ENDPOINT}")
        
        # Test redirect URI
        redirect_uri = hub_backend.get_redirect_uri()
        click.echo(f"   Redirect URI: {redirect_uri}")
        
        click.echo("✅ OIDC configuration appears valid")
        click.echo("\n🔗 To test the flow:")
        
        if HUGGINGFACE_SETTINGS.is_running_on_huggingface:
            space_id = HUGGINGFACE_SETTINGS.space_id
            click.echo(f"   1. Visit: https://{space_id}.hf.space/login")
            click.echo("   2. Click 'Sign in with Extralit Hub'")
        else:
            click.echo("   1. Visit your instance's login page")
            click.echo("   2. Click 'Sign in with Extralit Hub'")
            
    except Exception as e:
        click.echo(f"❌ OIDC test failed: {e}")
        exit(1)


@hub_auth_cli.command("clear-credentials")
@click.confirmation_option(prompt="Are you sure you want to clear stored credentials?")
def clear_credentials():
    """Clear stored Hub credentials."""
    click.echo("🗑️  Clearing stored credentials...")
    
    try:
        # Remove credentials file if it exists
        credentials_file = os.path.join(os.getcwd(), ".extralit_hub_credentials")
        if os.path.exists(credentials_file):
            os.remove(credentials_file)
            click.echo(f"   Removed: {credentials_file}")
        
        click.echo("✅ Credentials cleared")
        click.echo("   You'll need to re-register with: pdm run cli hub-auth register")
        
    except Exception as e:
        click.echo(f"❌ Failed to clear credentials: {e}")
        exit(1)


if __name__ == "__main__":
    hub_auth_cli()