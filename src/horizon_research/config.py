"""User configuration loading.

Reads horizon.toml from the workspace root and returns a HorizonConfig.
Falls back to defaults if the file is absent or a key is missing.

Schema (all keys optional):

  [horizon]
  project_dir = "project"           # relative to workspace
  governance_enabled = false
  literature_watch_enabled = false

This module is the only place that reads horizon.toml. All other modules
receive a HorizonConfig from the caller (testable, no filesystem coupling).
"""
from __future__ import annotations

from pathlib import Path

from .controlplane.context import HorizonConfig

_CONFIG_FILENAME = "horizon.toml"


def load_config(workspace: Path) -> HorizonConfig:
    """Read horizon.toml from workspace and return a HorizonConfig.

    Missing file → all defaults. Missing keys → field defaults.
    """
    config_path = workspace / _CONFIG_FILENAME
    if not config_path.exists():
        return HorizonConfig()

    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    section = raw.get("horizon", {})

    return HorizonConfig(
        project_dir=Path(section.get("project_dir", "project")),
        governance_enabled=bool(section.get("governance_enabled", False)),
        literature_watch_enabled=bool(section.get("literature_watch_enabled", False)),
    )
