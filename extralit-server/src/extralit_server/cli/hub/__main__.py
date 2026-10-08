from typer import Typer

from .auth import check_status, clear_credentials, register_instance, test_oidc_flow

# Create hub-auth subcommand group
app = Typer(help="Extralit Hub authentication management commands", no_args_is_help=True)
app.command(name="register", help="Register this instance with the Extralit Hub")(register_instance)
app.command(name="status", help="Check Hub authentication status")(check_status)
app.command(name="test", help="Test OIDC configuration and endpoints")(test_oidc_flow)
app.command(name="deregister", help="Clear stored Hub credentials")(clear_credentials)


if __name__ == "__main__":
    app()
