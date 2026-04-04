"""CLI entry point, argument parsing, and command dispatch.

All commands are grouped under the `horizon` root command.
Each command constructs a ProjectContext, wires a Gateway, and delegates
to the appropriate control-plane service.

Command surface (mirrors MCP tools):
  horizon register <resource> [options]
  horizon get <resource> <id>
  horizon list <resource>
  horizon transition <resource> <id> <status>
  horizon validate
  horizon health
  horizon status
  horizon run-script <script-id>
  horizon render [--force]
  horizon export [--format json|markdown] [--output PATH]
  horizon session open|close|list  (governance opt-in)
"""
from __future__ import annotations

from pathlib import Path

import click

from ...config import build_context, load_config
from .formatters import print_gateway_result, print_health_report, print_status


@click.group()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project workspace directory (defaults to cwd).",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def cli(ctx: click.Context, workspace: Path | None, output_json: bool) -> None:
    """Horizon Research — control plane for epistemic webs."""
    ws = workspace or Path.cwd()
    config = load_config(ws)
    context = build_context(ws, config)
    ctx.ensure_object(dict)
    ctx.obj["context"] = context
    ctx.obj["output_json"] = output_json


@cli.command()
@click.argument("resource")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def register(ctx: click.Context, resource: str, dry_run: bool) -> None:
    """Register a new resource entity. Reads payload from stdin as JSON."""
    raise NotImplementedError


@cli.command()
@click.argument("resource")
@click.argument("identifier")
@click.pass_context
def get(ctx: click.Context, resource: str, identifier: str) -> None:
    """Retrieve a single resource by ID."""
    raise NotImplementedError


@cli.command("list")
@click.argument("resource")
@click.pass_context
def list_resources(ctx: click.Context, resource: str) -> None:
    """List all resources of a given type."""
    raise NotImplementedError


@cli.command()
@click.argument("resource")
@click.argument("identifier")
@click.argument("new_status")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def transition(
    ctx: click.Context, resource: str, identifier: str, new_status: str, dry_run: bool
) -> None:
    """Transition a resource to a new status."""
    raise NotImplementedError


@cli.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Run all domain validators and print findings."""
    raise NotImplementedError


@cli.command()
@click.pass_context
def health(ctx: click.Context) -> None:
    """Run all health checks and print a structured report."""
    raise NotImplementedError


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Print a high-level project status dashboard."""
    raise NotImplementedError


@cli.command("run-script")
@click.argument("script_id")
@click.pass_context
def run_script(ctx: click.Context, script_id: str) -> None:
    """Run a registered verification script."""
    raise NotImplementedError


@cli.command()
@click.option("--force", is_flag=True, help="Re-render even if nothing has changed.")
@click.pass_context
def render(ctx: click.Context, force: bool) -> None:
    """Regenerate all view surfaces."""
    raise NotImplementedError


@cli.command()
@click.option(
    "--format", "fmt", type=click.Choice(["json", "markdown"]), default="json"
)
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
@click.pass_context
def export(ctx: click.Context, fmt: str, output: Path | None) -> None:
    """Bulk-export the epistemic web."""
    raise NotImplementedError


@cli.group()
def session() -> None:
    """Session management (governance opt-in)."""


@session.command("open")
@click.option("--summary", default=None)
@click.pass_context
def session_open(ctx: click.Context, summary: str | None) -> None:
    """Open a new research session."""
    raise NotImplementedError


@session.command("close")
@click.argument("session_number", type=int)
@click.option("--summary", default=None)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def session_close(
    ctx: click.Context, session_number: int, summary: str | None, dry_run: bool
) -> None:
    """Close a session through the close gate."""
    raise NotImplementedError


@session.command("list")
@click.pass_context
def session_list(ctx: click.Context) -> None:
    """List all sessions."""
    raise NotImplementedError
