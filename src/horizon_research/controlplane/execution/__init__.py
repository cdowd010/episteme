"""Execution pipeline for verification scripts.

Subsystems:
  scripts     — Registered script dispatch and result handling
  policy      — Execution policy normalization (sandbox, network, timeout)
  meta_verify — Adversarial integrity checks on script output
"""
