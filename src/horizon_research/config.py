"""Project configuration and runtime context.

This module is the single place for:
  - ProjectFeatures  — which opt-in features are enabled
  - HorizonConfig    — parsed from horizon.toml (or defaults)
  - ProjectPaths     — all filesystem paths derived from workspace + config
  - ProjectContext   — the runtime contract passed to every service
  - load_config()    — reads horizon.toml, returns HorizonConfig
  - build_context()  — derives all paths, returns ProjectContext

Every service receives a ProjectContext. No service reads horizon.toml
directly — all config is injected via ProjectContext.

horizon.toml schema (all keys optional):

  [horizon]
  project_dir = "project"     # relative to workspace root

  [features]
  goals = false
  inference_gap_analysis = false
  governance = false
  literature_watch = false
  experiment_ideation = false
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_CONFIG_FILENAME = "horizon.toml"


# ── Feature flags ─────────────────────────────────────────────────

@dataclass
class ProjectFeatures:
    """Opt-in capabilities. Each flag gates a set of MCP tools and CLI commands.

    Core tools (register, get, list, validate, health, render, export,
    check_stale, record_result) are always available — no flag needed.
    Feature tools register only when their flag is true.
    """
    goals: bool = False                  # goal tracking MCP tools + CLI commands
    inference_gap_analysis: bool = False # structural gap reporter (features/discovery.py)
    governance: bool = False             # sessions, boundaries, close gates
    literature_watch: bool = False       # post-Phase 7
    experiment_ideation: bool = False    # post-Phase 7


# ── User config (from horizon.toml) ──────────────────────────────

@dataclass
class HorizonConfig:
    """Parsed from horizon.toml. All fields have safe defaults."""
    project_dir: Path = field(default_factory=lambda: Path("project"))
    features: ProjectFeatures = field(default_factory=ProjectFeatures)


# ── Filesystem paths ──────────────────────────────────────────────

@dataclass
class ProjectPaths:
    """All filesystem paths derived from workspace root and config.

    Computed once at context-build time. Never re-derived at call time.
    """
    workspace: Path
    project_dir: Path
    data_dir: Path           # entity JSON files (claims.json, predictions.json, ...)
    views_dir: Path          # rendered markdown outputs
    cache_dir: Path
    render_cache_file: Path
    transaction_log_file: Path


# ── Runtime contract ──────────────────────────────────────────────

@dataclass
class ProjectContext:
    """Runtime contract passed to every service.

    Immutable after construction. Services must not store mutable state
    on the context — use it to locate resources, then do work locally.
    """
    workspace: Path
    config: HorizonConfig
    paths: ProjectPaths


# ── Builders ──────────────────────────────────────────────────────

def load_config(workspace: Path) -> HorizonConfig:
    """Read horizon.toml from workspace and return a HorizonConfig.

    Missing file → all defaults. Missing keys → field defaults.
    """
    config_path = workspace / _CONFIG_FILENAME
    if not config_path.exists():
        return HorizonConfig()

    try:
        import tomllib          # Python 3.11+
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    horizon = raw.get("horizon", {})
    feat = raw.get("features", {})

    return HorizonConfig(
        project_dir=Path(horizon.get("project_dir", "project")),
        features=ProjectFeatures(
            goals=bool(feat.get("goals", False)),
            inference_gap_analysis=bool(feat.get("inference_gap_analysis", False)),
            governance=bool(feat.get("governance", False)),
            literature_watch=bool(feat.get("literature_watch", False)),
            experiment_ideation=bool(feat.get("experiment_ideation", False)),
        ),
    )


def build_context(workspace: Path, config: HorizonConfig) -> ProjectContext:
    """Derive all paths from workspace root and config. Return a ProjectContext.

    This is the only place path derivation logic lives.
    """
    project_dir = workspace / config.project_dir
    data_dir = project_dir / "data"
    cache_dir = project_dir / ".cache"

    paths = ProjectPaths(
        workspace=workspace,
        project_dir=project_dir,
        data_dir=data_dir,
        views_dir=project_dir / "views",
        cache_dir=cache_dir,
        render_cache_file=cache_dir / "render.json",
        transaction_log_file=data_dir / "transaction_log.jsonl",
    )
    return ProjectContext(workspace=workspace, config=config, paths=paths)
