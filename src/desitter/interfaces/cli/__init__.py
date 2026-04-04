"""CLI adapter — secondary external interface for humans and scripts.

Uses Click for argument parsing and Rich for terminal output.
Every command routes through the Gateway or a read-only service.
There is no CLI-specific business logic.

Install: pip install "desitter"  (click + rich are core deps)
"""
