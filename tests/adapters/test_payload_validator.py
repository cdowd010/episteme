"""Tests for adapters/payload_validator.py."""
from __future__ import annotations

from desitter.adapters.payload_validator import JsonSchemaPayloadValidator
from desitter.epistemic.types import ClaimType, Severity


class TestJsonSchemaPayloadValidator:
    def test_optional_field_rejects_wrong_type(self):
        validator = JsonSchemaPayloadValidator()

        findings = validator.validate(
            "claim",
            {
                "id": "C-001",
                "statement": "Catalyst X increases yield.",
                "type": ClaimType.FOUNDATIONAL,
                "scope": "global",
                "falsifiability": "A repeated null result would falsify this claim.",
                "source": {"invalid": "object"},
            },
        )

        assert findings
        assert findings[0].severity == Severity.CRITICAL
        assert "payload.source" in findings[0].message

    def test_optional_field_accepts_null(self):
        validator = JsonSchemaPayloadValidator()

        findings = validator.validate(
            "claim",
            {
                "id": "C-001",
                "statement": "Catalyst X increases yield.",
                "type": ClaimType.FOUNDATIONAL,
                "scope": "global",
                "falsifiability": "A repeated null result would falsify this claim.",
                "source": None,
            },
        )

        assert findings == []
