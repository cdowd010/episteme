"""deSitter — control plane for research epistemic webs.

Layer cake (top to bottom):
  interfaces   — optional consumer adapters (CLI, MCP, REST, …)
  views        — read-only summaries and computed projections
  controlplane — orchestration boundary above the epistemic kernel
  epistemic    — domain kernel: EpistemicWeb, entities, invariants, ports
  local edge   — optional deployment adapters such as local workspaces

Programmatic entry point::

    from desitter.client import DeSitterClient, connect
"""

__version__ = "0.1.0"

from .client import ClientResult, DeSitterClient, DeSitterClientError, connect
