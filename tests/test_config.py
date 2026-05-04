"""Tests for validate_workspace in config.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from episteme.config import EpistemeConfig, ProjectPaths, ProjectContext, validate_workspace
from episteme.epistemic.types import Severity


def _make_context(root: Path) -> ProjectContext:
    """Build a ProjectContext whose paths are under *root*."""
    config = EpistemeConfig(project_dir=Path("project"))
    project_dir = root / "project"
    paths = ProjectPaths(
        root=root,
        project_dir=project_dir,
        data_dir=project_dir / "data",
        cache_dir=project_dir / ".cache",
    )
    return ProjectContext(workspace=root, config=config, paths=paths)


class TestValidateWorkspace:
    def test_all_present_returns_empty(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.paths.project_dir.mkdir(parents=True, exist_ok=True)
        ctx.paths.data_dir.mkdir(parents=True, exist_ok=True)
        findings = validate_workspace(ctx)
        assert findings == []

    def test_missing_project_dir_gives_warning(self, tmp_path):
        ctx = _make_context(tmp_path)
        # Neither project_dir nor data_dir exists
        findings = validate_workspace(ctx)
        sources = [f.source for f in findings]
        assert any("project_directory" in s for s in sources)

    def test_missing_data_dir_gives_warning(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.paths.project_dir.mkdir(parents=True, exist_ok=True)
        # data_dir still absent
        findings = validate_workspace(ctx)
        sources = [f.source for f in findings]
        assert any("data_directory" in s for s in sources)

    def test_findings_are_warnings_not_critical(self, tmp_path):
        ctx = _make_context(tmp_path)
        findings = validate_workspace(ctx)
        assert findings  # at least one
        for f in findings:
            assert f.severity == Severity.WARNING

    def test_only_project_dir_missing_one_finding(self, tmp_path):
        ctx = _make_context(tmp_path)
        # project_dir absent; data_dir is a sub-path so also absent
        findings = validate_workspace(ctx)
        # Both project_dir and data_dir are expected — both absent
        assert len(findings) == 2

    def test_only_data_dir_missing_one_finding(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.paths.project_dir.mkdir(parents=True, exist_ok=True)
        findings = validate_workspace(ctx)
        assert len(findings) == 1
        assert "data_directory" in findings[0].source
