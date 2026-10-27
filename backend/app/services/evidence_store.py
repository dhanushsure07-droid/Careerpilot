"""Small SQLite-backed evidence store.

SQLite is included with Python, persists to a local file, and is sufficient for
this single-process learning milestone. Candidate IDs scope every read/write;
they are not an authenticated identity until an auth system is added.
"""

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.models.evidence import PersistedCandidateEvidence, VerificationStatus


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "backend" / "data" / "careerpilot.sqlite3"


class DatabaseConfigurationError(ValueError):
    """Raised when the local SQLite path configuration is invalid."""


class EvidenceStore:
    """Persist candidate evidence in a local SQLite database."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        if database_path is not None:
            configured_path = str(database_path)
            source = "database_path"
        elif "CAREERPILOT_DB_PATH" in os.environ:
            configured_path = os.environ["CAREERPILOT_DB_PATH"]
            source = "CAREERPILOT_DB_PATH"
        else:
            configured_path = str(DEFAULT_DATABASE_PATH)
            source = "default database path"

        if not configured_path.strip():
            raise DatabaseConfigurationError(f"{source} must not be empty.")

        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        self.database_path = path.resolve()

    @staticmethod
    def _create_database_file(database_path: Path) -> None:
        """Create a new POSIX database file as owner-only; never chmod existing files."""

        if os.name != "posix":
            return

        try:
            file_descriptor = os.open(
                database_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            # Existing databases belong to the operator; do not silently alter
            # permissions on a file the application did not create.
            return
        os.close(file_descriptor)

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._create_database_file(self.database_path)
        connection = sqlite3.connect(self.database_path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS candidate_evidence (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    claim TEXT NOT NULL CHECK (length(trim(claim)) > 0),
                    source TEXT NOT NULL CHECK (length(trim(source)) > 0),
                    verification_status TEXT NOT NULL
                        CHECK (verification_status IN ('unverified', 'verified')),
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_candidate "
                "ON candidate_evidence(candidate_id, created_at)"
            )
        except BaseException:
            connection.close()
            raise
        return connection

    @staticmethod
    def _to_model(row: sqlite3.Row) -> PersistedCandidateEvidence:
        return PersistedCandidateEvidence(
            id=UUID(row["id"]),
            candidate_id=UUID(row["candidate_id"]),
            claim=row["claim"],
            source=row["source"],
            verification_status=VerificationStatus(row["verification_status"]),
            metadata=json.loads(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def create(
        self, candidate_id: UUID, *, claim: str, source: str, metadata: dict[str, str]
    ) -> PersistedCandidateEvidence:
        evidence = PersistedCandidateEvidence(
            candidate_id=candidate_id,
            claim=claim,
            source=source,
            metadata=metadata,
        )
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO candidate_evidence
                        (id, candidate_id, claim, source, verification_status,
                         metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(evidence.id),
                        str(candidate_id),
                        evidence.claim,
                        evidence.source,
                        evidence.verification_status.value,
                        json.dumps(evidence.metadata, sort_keys=True),
                        evidence.created_at.isoformat(),
                        evidence.updated_at.isoformat(),
                    ),
                )
        return evidence

    def get(
        self, candidate_id: UUID, evidence_id: UUID
    ) -> PersistedCandidateEvidence | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM candidate_evidence WHERE id = ? AND candidate_id = ?",
                (str(evidence_id), str(candidate_id)),
            ).fetchone()
        return self._to_model(row) if row else None

    def list_for_candidate(self, candidate_id: UUID) -> list[PersistedCandidateEvidence]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM candidate_evidence WHERE candidate_id = ? "
                "ORDER BY created_at, id",
                (str(candidate_id),),
            ).fetchall()
        return [self._to_model(row) for row in rows]

    def update_verification(
        self,
        candidate_id: UUID,
        evidence_id: UUID,
        verification_status: VerificationStatus,
    ) -> PersistedCandidateEvidence | None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE candidate_evidence
                    SET verification_status = ?, updated_at = ?
                    WHERE id = ? AND candidate_id = ?
                    """,
                    (
                        verification_status.value,
                        now,
                        str(evidence_id),
                        str(candidate_id),
                    ),
                )
                if cursor.rowcount == 0:
                    return None
                row = connection.execute(
                    "SELECT * FROM candidate_evidence WHERE id = ? AND candidate_id = ?",
                    (str(evidence_id), str(candidate_id)),
                ).fetchone()
        return self._to_model(row)
