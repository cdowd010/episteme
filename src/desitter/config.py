"""Project configuration and runtime context.

This module is the runtime configuration contract for the entire system.
``DesitterConfig`` holds settings parsed from ``desitter.toml``.
``ProjectPaths`` holds all derived filesystem paths.
``ProjectContext`` bundles the workspace path, config, and paths into
the single object passed through every service call.

Nothing in ``epistemic/``, ``controlplane/``, or ``views/`` needs this
module directly. It is consumed by the ``client`` package and by
interface adapters (CLI, MCP) at startup.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .epistemic.types import Finding

_CONFIG_FILENAME = "desitter.toml"


# ── Configuration ────────────────────────────────────────────────


@dataclass
class DesitterConfig:
    """Parsed project settings loaded from ``desitter.toml``.

    Attributes:
        project_dir: Project directory relative to the workspace root.
            Defaults to ``"project"``.
    """
    project_dir: Path = field(default_factory=lambda: Path("project"))


# ── Derived paths ────────────────────────────────────────────────


@dataclass
class ProjectPaths:
    """All filesystem paths derived from a workspace root.

    Computed once at startup by ``build_context()``. Never re-derived.

    Attributes:
        root: Absolute path to the workspace root directory.
        project_dir: Absolute path to the project directory.
        data_dir: Directory containing entity data files.
        cache_dir: Directory for internal caches.
    """
    root: Path
    project_dir: Path
    data_dir: Path
    cache_dir: Path


# ── Runtime context ──────────────────────────────────────────────


@dataclass
class ProjectContext:
    """Runtime context passed through every service call.

    Bundles the workspace path, the parsed config, and the computed
    paths into a single object. Constructed once at startup.

    Attributes:
        workspace: Absolute path to the workspace root.
        config: Parsed project configuration.
        paths: Derived filesystem paths.
    """
    workspace: Path
    config: DesitterConfig
    paths: ProjectPaths


# ── Builders ─────────────────────────────────────────────────────


def load_config(root: Path) -> DesitterConfig:
    """Read ``desitter.toml`` from *root* and return project settings.

    A missing file or missing keys are not errors — defaults are used.
    Only the ``[desitter]`` table is read.

    Args:
        root: Absolute path to the workspace root.

    Returns:
        DesitterConfig: Parsed configuration with defaults.
    """
    config_path = root / _CONFIG_FILENAME
    if not config_path.exists():
        return DesitterConfig()

    try:
        import tomllib          # Python 3.11+
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    desitter = raw.get("desitter", {})

    return DesitterConfig(
        project_dir=Path(desitter.get("project_dir", "project")),
    )


def build_context(
    root: Path,
    config: DesitterConfig | None = None,
) -> ProjectContext:
    """Derive the runtime context for a workspace root.

    This is the single place the default directory layout is derived.
    Callers supply a workspace root and optionally a pre-loaded config.

    Args:
        root: Absolute path to the workspace root.
        config: Parsed configuration. When ``None``, the configuration
            is loaded from disk via ``load_config``.

    Returns:
        ProjectContext: The assembled runtime context.
    """
    resolved_config = config or load_config(root)
    project_dir = root / resolved_config.project_dir
    data_dir = project_dir / "data"
    cache_dir = project_dir / ".cache"

    paths = ProjectPaths(
        root=root,
        project_dir=project_dir,
        data_dir=data_dir,
        cache_dir=cache_dir,
    )
    return ProjectContext(workspace=root, config=resolved_config, paths=paths)


def validate_workspace(context: ProjectContext) -> list[Finding]:
    """Validate the expected directory layout for a workspace.

    Checks that the expected directories exist and are accessible.

    Args:
        context: The runtime context to validate.

    Returns:
        list[Finding]: Findings for missing or unexpected paths.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError
