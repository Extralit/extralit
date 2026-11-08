import asyncio
from typing import Optional

import typer

app = typer.Typer(help="Chunk and embed the layout store", no_args_is_help=True)


@app.command(
    name="backfill", help="Enqueue chunk jobs for unchunked or stale documents, then an embed job per workspace"
)
def backfill(workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Only this workspace")) -> None:
    from extralit_server.contexts.retrieval.backfill import backfill as run

    for report in asyncio.run(run(workspace)):
        pending = "n/a (no embedding model)" if report.unembedded is None else report.unembedded
        typer.echo(
            f"{report.workspace}: chunk_jobs={report.chunk_jobs} embed_job={report.embed_job} unembedded_before={pending}"
        )
