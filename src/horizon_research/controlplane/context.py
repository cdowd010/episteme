"""ProjectContext: the single runtime contract for all control-plane services.

Every control-plane service receives a ProjectContext and uses it to locate
paths, read config, and access caches. No module-level globals. No
monkey-patching. ProjectContext carries data, not callbacks.

Usage:
    config = load_config(workspace)
    ctx = build_context(workspace, config)
    gateway = Gateway(ctx, repo, validator, renderer, prose_sync, tx_log)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class HorizonConfig:
    """User-facing configuration loaded from horizon.toml (or defaults).

    project_dir: path to the canonical data directory, relative to workspace.
    governance_enabled: opt-in session boundary enforcement.
    literature_watch_enabled: opt-in background literature monitoring.
    """
    project_dir: Path = Path("project")
    governance_enabled: bool = False
    literature_watch_enabled: bool = False


@dataclass
class ProjectPaths:
    """All filesystem paths derived from workspace root and config.

    Computed once at context-build time. Never re-derived at call time.
    """
    workspace: Path
    project_dir: Path
    data_dir: Path
    views_dir: Path
    knowledge_dir: Path
    integrity_dir: Path
    verify_script_dir: Path
    analysis_script_dir: Path
    cache_dir: Path
    render_cache_file: Path
    check_refs_cache_file: Path
    query_transaction_log_file: Path


@dataclass
class ProjectContext:
    """Runtime contract passed to every control-plane service.

    Immutable after construction. Services must not store mutable state
    on the context — use it to locate resources, then do work locally.
    """
    workspace: Path
    config: HorizonConfig
    paths: ProjectPaths


def load_config(workspace: Path) -> HorizonConfig:
    """Load horizon.toml from workspace, falling back to defaults.

    Returns a HorizonConfig with all fields populated.
    """
    raise NotImplementedError


def build_context(workspace: Path, config: HorizonConfig) -> ProjectContext:
    """Derive all paths from workspace root and config, return a ProjectContext.

    This is the only place path derivation logic lives.
    """
    raise NotImplementedError
