from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import jwt
import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth import (
    AuthConfigurationError,
    AuthServiceUnavailable,
    InvalidAccessToken,
    SupabaseAuthConfig,
    SupabaseTokenVerifier,
)
from app.services.evidence_store import EvidenceStore


PROJECT_URL = "https://careerpilot-test.supabase.co"
PUBLISHABLE_KEY = "sb_publishable_test_value"
USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


class FixedJwksClient:
    """Avoid network access while leaving PyJWT to verify the real signature."""

    def __init__(self, public_key):
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token: str):
        header = jwt.get_unverified_header(token)
        assert header["kid"] == "careerpilot-test-key"
        return SimpleNamespace(key=self.public_key)


@pytest.fixture
def signing_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def make_rsa_token(
    private_key, *, user_id: UUID = USER_ID, claims_override: dict | None = None
) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "iss": f"{PROJECT_URL}/auth/v1",
        "aud": "authenticated",
        "sub": str(user_id),
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(claims_override or {})
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "careerpilot-test-key"},
    )


def make_verifier(public_key) -> SupabaseTokenVerifier:
    return SupabaseTokenVerifier(
        SupabaseAuthConfig(PROJECT_URL, PUBLISHABLE_KEY),
        jwks_client=FixedJwksClient(public_key),
    )


def test_valid_signed_supabase_user_token_authenticates_user(signing_keys) -> None:
    private_key, public_key = signing_keys
    verifier = make_verifier(public_key)

    assert verifier.verify(make_rsa_token(private_key)) == USER_ID


@pytest.mark.parametrize(
    "token",
    ["not-a-jwt", "eyJhbGciOiJub25lIn0.eyJzdWIiOiJzb21lb25lIn0."],
)
def test_malformed_or_unapproved_algorithm_token_is_rejected(
    signing_keys, token: str
) -> None:
    _private_key, public_key = signing_keys

    with pytest.raises(InvalidAccessToken):
        make_verifier(public_key).verify(token)


def test_invalid_signature_is_rejected(signing_keys) -> None:
    _trusted_private_key, trusted_public_key = signing_keys
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(InvalidAccessToken):
        make_verifier(trusted_public_key).verify(make_rsa_token(attacker_key))


@pytest.mark.parametrize(
    "claims_override",
    [
        {"iss": "https://another-project.supabase.co/auth/v1"},
        {"aud": "anon"},
        {"role": "service_role"},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
    ],
)
def test_wrong_project_or_non_user_claims_are_rejected(
    signing_keys, claims_override: dict
) -> None:
    private_key, public_key = signing_keys

    with pytest.raises(InvalidAccessToken):
        make_verifier(public_key).verify(
            make_rsa_token(private_key, claims_override=claims_override)
        )


def test_valid_token_authenticates_and_owns_candidate_routes(
    tmp_path, signing_keys
) -> None:
    private_key, public_key = signing_keys
    client = TestClient(
        create_app(
            EvidenceStore(tmp_path / "auth-api.sqlite3"),
            token_verifier=make_verifier(public_key),
        )
    )
    token = make_rsa_token(private_key)
    response = client.post(
        f"/candidates/{USER_ID}/evidence",
        headers={"Authorization": f"Bearer {token}"},
        json={"claim": "Built a project", "source": "Portfolio"},
    )

    assert response.status_code == 201
    assert response.json()["candidate_id"] == str(USER_ID)
    evidence_id = response.json()["id"]
    assert client.get(
        f"/candidates/{USER_ID}/evidence",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 200
    assert client.get(
        f"/candidates/{USER_ID}/evidence/{evidence_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 200
    assert client.patch(
        f"/candidates/{USER_ID}/evidence/{evidence_id}/verification",
        headers={"Authorization": f"Bearer {token}"},
        json={"verification_status": "verified"},
    ).status_code == 200
    assert client.get(
        f"/candidates/{uuid4()}/evidence",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 403


def test_hs256_token_is_validated_by_supabase_user_endpoint(monkeypatch) -> None:
    config = SupabaseAuthConfig(PROJECT_URL, PUBLISHABLE_KEY)
    verifier = SupabaseTokenVerifier(config)
    test_token = jwt.encode(
        {"sub": str(USER_ID)}, "test-only-shared-secret-that-is-long-enough", algorithm="HS256"
    )
    observed = {}

    def fake_get(url, *, headers, timeout):
        observed.update(url=url, headers=headers, timeout=timeout)
        return SimpleNamespace(status_code=200, json=lambda: {"id": str(USER_ID)})

    monkeypatch.setattr("app.services.auth.httpx.get", fake_get)

    assert verifier.verify(test_token) == USER_ID
    assert observed["url"] == f"{PROJECT_URL}/auth/v1/user"
    assert observed["headers"]["apikey"] == PUBLISHABLE_KEY
    assert observed["headers"]["Authorization"] == f"Bearer {test_token}"


@pytest.mark.parametrize("status_code", [401, 403])
def test_hs256_token_rejected_when_auth_server_rejects_it(
    monkeypatch, status_code: int
) -> None:
    verifier = SupabaseTokenVerifier(SupabaseAuthConfig(PROJECT_URL, PUBLISHABLE_KEY))
    test_token = jwt.encode(
        {"sub": str(USER_ID)},
        "test-only-shared-secret-that-is-long-enough",
        algorithm="HS256",
    )
    monkeypatch.setattr(
        "app.services.auth.httpx.get",
        lambda *_args, **_kwargs: SimpleNamespace(status_code=status_code),
    )

    with pytest.raises(InvalidAccessToken):
        verifier.verify(test_token)


@pytest.mark.parametrize("status_code", [429, 500])
def test_hs256_token_auth_service_errors_are_unavailable(
    monkeypatch, status_code: int
) -> None:
    verifier = SupabaseTokenVerifier(SupabaseAuthConfig(PROJECT_URL, PUBLISHABLE_KEY))
    test_token = jwt.encode(
        {"sub": str(USER_ID)},
        "test-only-shared-secret-that-is-long-enough",
        algorithm="HS256",
    )
    monkeypatch.setattr(
        "app.services.auth.httpx.get",
        lambda *_args, **_kwargs: SimpleNamespace(status_code=status_code),
    )

    with pytest.raises(AuthServiceUnavailable):
        verifier.verify(test_token)


@pytest.mark.parametrize(
    "network_error",
    [httpx.ConnectError("connection failed"), httpx.TimeoutException("request timed out")],
)
def test_hs256_token_network_failures_are_unavailable(
    monkeypatch, network_error: httpx.RequestError
) -> None:
    verifier = SupabaseTokenVerifier(SupabaseAuthConfig(PROJECT_URL, PUBLISHABLE_KEY))
    test_token = jwt.encode(
        {"sub": str(USER_ID)},
        "test-only-shared-secret-that-is-long-enough",
        algorithm="HS256",
    )

    def fail_request(*_args, **_kwargs):
        raise network_error

    monkeypatch.setattr("app.services.auth.httpx.get", fail_request)

    with pytest.raises(AuthServiceUnavailable):
        verifier.verify(test_token)


def test_publishable_key_is_not_accepted_as_a_bearer_token(monkeypatch) -> None:
    verifier = SupabaseTokenVerifier(
        SupabaseAuthConfig(PROJECT_URL, PUBLISHABLE_KEY)
    )

    def unexpected_auth_call(*_args, **_kwargs):
        raise AssertionError("API key must not be sent as an access token")

    monkeypatch.setattr("app.services.auth.httpx.get", unexpected_auth_call)

    with pytest.raises(InvalidAccessToken):
        verifier.verify(PUBLISHABLE_KEY)


def test_root_dotenv_file_is_loaded_without_overriding_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    (tmp_path / ".env").write_text(
        "SUPABASE_URL=https://dotenv-project.supabase.co\n"
        "SUPABASE_PUBLISHABLE_KEY=sb_publishable_from_dotenv\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.services.auth.PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)

    config = SupabaseAuthConfig.from_environment()

    assert config.supabase_url == "https://dotenv-project.supabase.co"
    assert config.publishable_key == "sb_publishable_from_dotenv"


def test_missing_supabase_configuration_is_reported_without_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr("app.services.auth.PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)

    with pytest.raises(AuthConfigurationError, match="SUPABASE_URL"):
        SupabaseAuthConfig.from_environment()


def test_non_local_supabase_url_requires_https(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr("app.services.auth.PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("SUPABASE_URL", "http://auth.example.com")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", PUBLISHABLE_KEY)

    with pytest.raises(AuthConfigurationError, match="must use HTTPS"):
        SupabaseAuthConfig.from_environment()
