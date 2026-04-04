"""CLI adapter — secondary external interface for humans and scripts.

Uses Click for argument parsing and Rich for terminal output.
Every command routes through the Gateway or a read-only service.
There is no CLI-specific business logic.

Install: pip install "horizon-research"  (click + rich are core deps)
"""
