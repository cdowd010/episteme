"""Transaction log: implements TransactionLog.

Appends a provenance record for every successful gateway mutation.
Records are newline-delimited JSON written to
    project/data/transaction_log.jsonl

Implements the TransactionLog protocol from epistemic/ports.py.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class JsonTransactionLog:
    """Append-only JSONL transaction log for operation provenance.

    Every successful gateway mutation appends a newline-delimited JSON
    record to the log file. Each record contains a UUID4 transaction ID,
    ISO 8601 UTC timestamp, operation descriptor, and entity identifier.

    Implements the ``TransactionLog`` protocol from ``epistemic/ports.py``.

    Attributes:
        _log_file: Path to the ``.jsonl`` log file (created if missing).
    """

    def __init__(self, log_file: Path) -> None:
        """Create a transaction log writer for a JSONL provenance file.

        Args:
            log_file: Path to the append-only JSONL log file.
        """
        self._log_file = log_file

    def append(self, operation: str, identifier: str) -> str:
        """Append a provenance record and return the transaction ID.

        Creates the log file's parent directory if it does not exist.
        Each record is a single JSON line with the schema::

            {
                "tx_id":      "<uuid4>",
                "timestamp":  "<ISO 8601 UTC>",
                "operation":  "<operation>",
                "identifier": "<identifier>"
            }

        Args:
            operation: A colon-delimited operation descriptor, e.g.
                ``"register:claim"`` or ``"set:parameter"``.
            identifier: The ID of the entity affected.

        Returns:
            str: A UUID4 transaction ID uniquely identifying this record.
        """
        tx_id = str(uuid.uuid4())
        record = {
            "tx_id": tx_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "identifier": identifier,
        }
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        with self._log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        return tx_id

    def read_all(self) -> list[dict]:
        """Return all records in the log, oldest first.

        Parses each line of the JSONL file as a JSON object. Blank
        lines are silently skipped.

        Returns:
            list[dict]: All provenance records in chronological order.
                Returns an empty list if the log file does not exist.
        """
        if not self._log_file.exists():
            return []
        records = []
        for line in self._log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records
