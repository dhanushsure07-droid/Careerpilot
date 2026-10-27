import os
import sqlite3
import stat
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.evidence import CandidateEvidence, PersistedCandidateEvidence, VerificationStatus
from app.services.evidence_store import (
    PROJECT_ROOT,
    DatabaseConfigurationError,
    EvidenceStore,
)


@pytest.fixture
def client(tmp_path):
    store = EvidenceStore(tmp_path / "test-evidence.sqlite3")
    return TestClient(create_app(store))


def test_create_list_and_get_evidence_for_candidate(client: TestClient) -> None:
    candidate_id = uuid4()
    response = client.post(
        f"/candidates/{candidate_id}/evidence",
        json={
            "claim": "Built an internal reporting dashboard",
            "source": "Portfolio project: reporting dashboard",
            "metadata": {"project": "reporting"},
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["candidate_id"] == str(candidate_id)
    assert created["verification_status"] == "unverified"
    assert created["source"] == "Portfolio project: reporting dashboard"
    assert created["metadata"] == {"project": "reporting"}
    assert created["created_at"]
    assert created["updated_at"]

    listed = client.get(f"/candidates/{candidate_id}/evidence")
    fetched = client.get(
        f"/candidates/{candidate_id}/evidence/{created['id']}"
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_evidence_persists_across_store_instances(tmp_path) -> None:
    database_path = tmp_path / "persistent-test.sqlite3"
    candidate_id = uuid4()
    first_store = EvidenceStore(database_path)
    created = first_store.create(
        candidate_id,
        claim="Completed a verified project",
        source="Project archive",
        metadata={"year": "2025"},
    )

    second_store = EvidenceStore(database_path)
    loaded = second_store.get(candidate_id, created.id)

    assert loaded == created


def test_persisted_evidence_requires_candidate_id_but_validation_model_does_not() -> None:
    assert CandidateEvidence(claim="A claim", source="A source").candidate_id is None
    assert PersistedCandidateEvidence.model_fields["candidate_id"].is_required()


def test_candidate_scoping_hides_and_protects_other_candidate_evidence(
    client: TestClient,
) -> None:
    owner_id = uuid4()
    other_id = uuid4()
    created = client.post(
        f"/candidates/{owner_id}/evidence",
        json={"claim": "Owned claim", "source": "Owned source"},
    ).json()
    evidence_id = created["id"]

    assert client.get(f"/candidates/{other_id}/evidence").json() == []
    assert (
        client.get(f"/candidates/{other_id}/evidence/{evidence_id}").status_code
        == 404
    )
    assert (
        client.patch(
            f"/candidates/{other_id}/evidence/{evidence_id}/verification",
            json={"verification_status": "verified"},
        ).status_code
        == 404
    )

    still_owned = client.get(f"/candidates/{owner_id}/evidence/{evidence_id}")
    assert still_owned.json()["verification_status"] == "unverified"


def test_missing_evidence_returns_not_found_for_get_and_update(
    client: TestClient,
) -> None:
    candidate_id = uuid4()
    evidence_id = uuid4()

    assert client.get(
        f"/candidates/{candidate_id}/evidence/{evidence_id}"
    ).status_code == 404
    assert (
        client.patch(
            f"/candidates/{candidate_id}/evidence/{evidence_id}/verification",
            json={"verification_status": "verified"},
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"claim": "", "source": "A source"},
        {"claim": "A claim", "source": ""},
        {"claim": "   ", "source": "A source"},
        {"claim": "A claim", "source": "A source", "metadata": {"year": 2}},
        {
            "claim": "A claim",
            "source": "A source",
            "verification_status": "verified",
        },
        {
            "claim": "A claim",
            "source": "A source",
            "candidate_id": str(uuid4()),
        },
    ],
)
def test_invalid_evidence_input_returns_validation_error(
    client: TestClient, payload: dict
) -> None:
    response = client.post(f"/candidates/{uuid4()}/evidence", json=payload)

    assert response.status_code == 422


def test_invalid_verification_status_returns_validation_error(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/candidates/{uuid4()}/evidence/{uuid4()}/verification",
        json={"verification_status": "maybe"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/candidates/not-a-uuid/evidence"),
        ("get", f"/candidates/{uuid4()}/evidence/not-a-uuid"),
        (
            "patch",
            f"/candidates/{uuid4()}/evidence/not-a-uuid/verification",
        ),
    ],
)
def test_malformed_path_uuids_return_validation_error(
    client: TestClient, method: str, path: str
) -> None:
    request = getattr(client, method)
    response = request(path, json={"verification_status": "verified"}) if method == "patch" else request(path)

    assert response.status_code == 422


def test_verification_update_preserves_provenance_and_creation_time(
    client: TestClient,
) -> None:
    candidate_id = uuid4()
    created = client.post(
        f"/candidates/{candidate_id}/evidence",
        json={
            "claim": "Delivered a data migration",
            "source": "Work record, migration project",
            "metadata": {"team": "platform", "year": "2024"},
        },
    ).json()

    response = client.patch(
        f"/candidates/{candidate_id}/evidence/{created['id']}/verification",
        json={"verification_status": VerificationStatus.VERIFIED.value},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["verification_status"] == "verified"
    assert updated["claim"] == created["claim"]
    assert updated["source"] == created["source"]
    assert updated["metadata"] == created["metadata"]
    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] >= created["updated_at"]


def test_empty_database_path_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAREERPILOT_DB_PATH", "")

    with pytest.raises(DatabaseConfigurationError, match="must not be empty"):
        EvidenceStore()


def test_relative_database_path_is_resolved_from_project_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CAREERPILOT_DB_PATH", "local-data/evidence.sqlite3")

    store = EvidenceStore()

    assert store.database_path == (PROJECT_ROOT / "local-data/evidence.sqlite3").resolve()
    assert not store.database_path.is_relative_to(tmp_path)


@pytest.mark.skipif(os.name != "posix", reason="POSIX file mode semantics required")
def test_new_database_file_is_owner_only(tmp_path) -> None:
    database_path = tmp_path / "private.sqlite3"
    store = EvidenceStore(database_path)
    store.create(uuid4(), claim="A claim", source="A source", metadata={})

    permissions = stat.S_IMODE(database_path.stat().st_mode)
    assert permissions & 0o077 == 0


@pytest.mark.skipif(os.name != "posix", reason="POSIX file mode semantics required")
def test_existing_database_file_permissions_are_not_changed(tmp_path) -> None:
    database_path = tmp_path / "existing.sqlite3"
    database_path.touch()
    database_path.chmod(0o640)
    store = EvidenceStore(database_path)

    store.create(uuid4(), claim="A claim", source="A source", metadata={})

    assert stat.S_IMODE(database_path.stat().st_mode) == 0o640


def test_connection_is_closed_when_schema_initialization_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    class FailingConnection:
        row_factory = None
        closed = False

        def execute(self, *_args):
            raise sqlite3.OperationalError("simulated schema error")

        def close(self):
            self.closed = True

    connection = FailingConnection()
    monkeypatch.setattr(
        "app.services.evidence_store.sqlite3.connect", lambda *_args: connection
    )

    with pytest.raises(sqlite3.OperationalError, match="simulated schema error"):
        EvidenceStore(tmp_path / "initialization-failure.sqlite3")._connect()

    assert connection.closed
