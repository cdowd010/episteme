"""Entry point for `python -m desitter`.

Delegates to the Click CLI, so:
    python -m desitter <command> [options]
is equivalent to:
    ds <command> [options]
"""
from desitter.interfaces.cli.main import cli

if __name__ == "__main__":
    cli()
