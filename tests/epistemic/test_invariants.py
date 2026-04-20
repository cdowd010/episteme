"""Tests for on-demand semantic invariant validators."""
from __future__ import annotations

from episteme.epistemic.model import TheoryId, TheoryStatus
from episteme.epistemic.invariants import validate_all


def test_theory_abandonment_impact(base_web):
    """Claims whose only motivating theory is ABANDONED should trigger a warning."""
    web = base_web.transition_theory(TheoryId("T-001"), TheoryStatus.ABANDONED)
    findings = validate_all(web)
    assert any("theoretical motivation" in f.message for f in findings)


def test_load_bearing_assumption_untested(base_web):
    """LOAD_BEARING assumptions with no tested_by links should trigger a critical finding."""
    findings = validate_all(base_web)
    assert any("LOAD_BEARING" in f.message for f in findings)
