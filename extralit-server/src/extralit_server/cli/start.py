import typer


def start(
    host: str = typer.Option("0.0.0.0", help="The host where the Extralit server will be binded"),
    port: int = typer.Option(6900, help="The port where the Extralit server will be binded"),
    access_log: bool = typer.Option(True, help="Whether to enable or disable the Extralit server access log"),
) -> None:
    import uvicorn

    uvicorn.run(
        "extralit_server:app",
        port=port,
        host=host,
        access_log=access_log,
    )
