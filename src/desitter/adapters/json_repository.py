"""JSON-backed implementation of WebRepository.

Loads and saves the epistemic web as a collection of JSON files under
project/data/. Each entity type has its own file:
  claims.json, assumptions.json, predictions.json, analyses.json,
    theories.json, independence_groups.json, pairwise_separations.json,
    discoveries.json, dead_ends.json, parameters.json

Implements the WebRepository protocol from epistemic/ports.py.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..epistemic.codec import build_entity, entity_to_dict
from ..epistemic.web import EpistemicWeb


_RESOURCE_FILES: dict[str, str] = {
    "parameters": "parameters.json",
    "analyses": "analyses.json",
    "assumptions": "assumptions.json",
    "claims": "claims.json",
    "independence_groups": "independence_groups.json",
    "predictions": "predictions.json",
    "theories": "theories.json",
    "discoveries": "discoveries.json",
    "dead_ends": "dead_ends.json",
    "pairwise_separations": "pairwise_separations.json",
}
"""Mapping of collection attribute names to their JSON filenames on disk."""

_LOAD_PLAN: list[tuple[str, str]] = [
    ("parameter", "parameters"),
    ("analysis", "analyses"),
    ("assumption", "assumptions"),
    ("claim", "claims"),
    ("independence_group", "independence_groups"),
    ("prediction", "predictions"),
    ("theory", "theories"),
    ("discovery", "discoveries"),
    ("dead_end", "dead_ends"),
    ("pairwise_separation", "pairwise_separations"),
]
"""Ordered loading plan as ``(singular_resource, collection_name)`` tuples.

Order matters: entities that are referenced by later entities must be
loaded first (e.g. parameters before analyses, assumptions before claims).
"""

_REGISTER_METHODS: dict[str, str] = {
    "parameter": "register_parameter",
    "analysis": "register_analysis",
    "assumption": "register_assumption",
    "claim": "register_claim",
    "independence_group": "register_independence_group",
    "prediction": "register_prediction",
    "theory": "register_theory",
    "discovery": "register_discovery",
    "dead_end": "register_dead_end",
    "pairwise_separation": "add_pairwise_separation",
}
"""Mapping of singular resource keys to their EpistemicWeb registration method names."""


class JsonRepository:
    """JSON-backed implementation of the ``WebRepository`` protocol.

    Loads and saves the epistemic web as a collection of JSON files under
    a project data directory. Each entity type has its own file (e.g.
    ``claims.json``, ``predictions.json``). Files are loaded in dependency
    order so that referenced entities exist before referencing entities
    are registered.

    Saves are atomic: data is written to a temporary file first, then
    renamed into place to avoid partial writes on crash.

    Attributes:
        _data_dir: The ``project/data/`` directory containing entity JSON files.
    """

    def __init__(self, data_dir: Path) -> None:
        """Create a repository bound to a project data directory.

        Args:
            data_dir: Directory containing per-entity JSON files.
        """
        self._data_dir = data_dir

    def load(self) -> EpistemicWeb:
        """Deserialize all entity JSON files and return a fully hydrated EpistemicWeb.

        Loads files in dependency order (parameters first, pairwise separations
        last) and replays each entity through the web's register methods to
        reconstruct all bidirectional links. Missing files are treated as
        empty registries (not an error).

        Returns:
            EpistemicWeb: A fully hydrated web with all entities and
                bidirectional links reconstructed from disk.

        Raises:
            TypeError: If a JSON file contains a non-list top-level structure
                or a non-object item.
        """
        web = EpistemicWeb()

        for resource, collection_name in _LOAD_PLAN:
            raw_items = self._load_file(_RESOURCE_FILES[collection_name])
            if not isinstance(raw_items, list):
                raise TypeError(
                    f"Expected list payload in {_RESOURCE_FILES[collection_name]!r}, "
                    f"got {type(raw_items)!r}"
                )
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    raise TypeError(
                        f"Expected object payload in {_RESOURCE_FILES[collection_name]!r}, "
                        f"got {type(raw_item)!r}"
                    )
                entity = build_entity(resource, raw_item)
                # Bind against the current web each iteration since register_* returns a
                # new EpistemicWeb instance.
                web = getattr(web, _REGISTER_METHODS[resource])(entity)

        return web

    def save(self, web: EpistemicWeb) -> None:
        """Serialize the web to JSON files, one per entity type.

        Creates the data directory if it does not exist. Each file is
        written atomically (write to a ``.json.tmp`` temp file, then
        rename) to avoid partial writes on crash. Entities within each
        file are sorted by ID for deterministic output.

        Args:
            web: The complete epistemic web to persist.
        """
        self._data_dir.mkdir(parents=True, exist_ok=True)

        for collection_name, file_name in _RESOURCE_FILES.items():
            registry = getattr(web, collection_name)
            serialized = [
                entity_to_dict(entity)
                for _, entity in sorted(registry.items(), key=lambda item: str(item[0]))
            ]
            self._write_file(file_name, serialized)

    def _load_file(self, name: str) -> list[dict]:
        """Read and parse a single entity JSON file.

        Args:
            name: The filename to load (e.g. ``"claims.json"``).

        Returns:
            list[dict]: The parsed JSON content as a list of dicts.
                Returns an empty list if the file does not exist.
        """
        path = self._data_dir / name
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_file(self, name: str, data: list[dict]) -> None:
        """Write entity data to a JSON file atomically.

        Writes to a ``.json.tmp`` temporary file first, then renames
        into place to ensure the final file is always complete.

        Args:
            name: The target filename (e.g. ``"claims.json"``).
            data: The serialized entity list to write.
        """
        path = self._data_dir / name
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(data, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
