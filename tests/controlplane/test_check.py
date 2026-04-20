"""Tests for the controlplane check module."""
from __future__ import annotations

from desitter.controlplane.check import check_stale


def test_check_stale_detects_outdated_analysis(base_web):
    """An analysis whose parameter was modified after the last run should be reported stale.

    base_web has PAR-001 last_modified=2026-04-10 and AN-001 last_result_date=2026-04-05,
    so AN-001 is stale.
    """
    findings = check_stale(base_web)
    assert any("stale" in f.message.lower() or "modified" in f.message.lower() for f in findings)
