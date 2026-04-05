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


class JsonRepository:
    """Loads and saves the epistemic web as JSON files on disk.

    data_dir: the project/data/ directory containing entity JSON files.
    """

    def __init__(self, data_dir: Path) -> None:
        """Create a repository bound to a project data directory.

        Args:
            data_dir: Directory containing per-entity JSON files.
        """
        self._data_dir = data_dir

    def load(self) -> EpistemicWeb:
        """Deserialise all entity JSON files and return a fully hydrated EpistemicWeb.

        Reads ``_metadata.json`` to restore the web version counter.
        Missing files are treated as empty registries (not an error).
        """
        metadata_path = self._data_dir / "_metadata.json"
        version = 0
        if metadata_path.exists():
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            version = int(meta.get("version", 0))

        web = EpistemicWeb(version=version)

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
                web = getattr(web, _REGISTER_METHODS[resource])(entity)

        return web

    def save(self, web: EpistemicWeb) -> None:
        """Serialise the web to JSON files, one per entity type.

        Increments ``web.version`` before writing and persists the new
        value in ``_metadata.json`` so that ``load()`` can restore it.
        Writes atomically (write to temp file, then rename) to avoid
        partial writes on crash.
        """
        self._data_dir.mkdir(parents=True, exist_ok=True)

        web.version += 1
        meta_tmp = self._data_dir / "_metadata.json.tmp"
        meta_tmp.write_text(
            json.dumps({"version": web.version}),
            encoding="utf-8",
        )
        meta_tmp.replace(self._data_dir / "_metadata.json")

        for collection_name, file_name in _RESOURCE_FILES.items():
            registry = getattr(web, collection_name)
            serialized = [
                entity_to_dict(entity)
                for _, entity in sorted(registry.items(), key=lambda item: str(item[0]))
            ]
            self._write_file(file_name, serialized)

    def _load_file(self, name: str) -> list[dict]:
        """Read and parse a single entity JSON file.

        Returns an empty list if the file doesn't exist.
        """
        path = self._data_dir / name
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_file(self, name: str, data: list[dict]) -> None:
        """Write entity data to a JSON file atomically."""
        path = self._data_dir / name
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(data, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
