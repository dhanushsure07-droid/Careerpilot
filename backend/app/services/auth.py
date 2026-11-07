"""Supabase access-token verification for protected API routes."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit
from uuid import UUID

import httpx
import jwt
from dotenv import load_dotenv
from jwt import PyJWKClient

from app.services.evidence_store import PROJECT_ROOT


class AuthConfigurationError(ValueError):
    """Raised when the Supabase project configuration is missing or invalid."""


class InvalidAccessToken(ValueError):
    """Raised when a bearer token cannot be verified as a Supabase user token."""


class AuthServiceUnavailable(RuntimeError):
    """Raised when remote Supabase verification cannot be completed."""


@dataclass(frozen=True)
class SupabaseAuthConfig:
    """Public project settings needed to verify user access tokens."""

    supabase_url: str
    publishable_key: str

    @property
    def issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"

    @property
    def user_url(self) -> str:
        return f"{self.issuer}/user"

    @classmethod
    def from_environment(cls) -> "SupabaseAuthConfig":
        # Root .env is git-ignored. Existing process environment takes precedence.
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
        publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip()
        if not supabase_url:
            raise AuthConfigurationError("SUPABASE_URL is not configured.")
        if not publishable_key:
            raise AuthConfigurationError("SUPABASE_PUBLISHABLE_KEY is not configured.")

        parsed_url = urlsplit(supabase_url)
        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise AuthConfigurationError("SUPABASE_URL must be a valid project URL.")
        if parsed_url.scheme == "http" and parsed_url.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise AuthConfigurationError(
                "SUPABASE_URL must use HTTPS except for a local Supabase instance."
            )
        return cls(supabase_url=supabase_url, publishable_key=publishable_key)


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> "SigningKey": ...


class SigningKey(Protocol):
    key: object


class TokenVerifier(Protocol):
    def verify(self, access_token: str) -> UUID: ...


class SupabaseTokenVerifier:
    """Verify asymmetric tokens locally and shared-secret tokens with Supabase."""

    _ASYMMETRIC_ALGORITHMS = {"ES256", "RS256"}

    def __init__(
        self,
        config: SupabaseAuthConfig,
        *,
        jwks_client: SigningKeyClient | None = None,
    ) -> None:
        self.config = config
        # Keep PyJWT's bounded JWKS-set cache; do not cache individual keys
        # indefinitely so signing-key rotations can be observed after refresh.
        self.jwks_client = jwks_client or PyJWKClient(config.jwks_url, timeout=5)

    def verify(self, access_token: str) -> UUID:
        """Return the Supabase auth.users UUID only after server verification."""

        try:
            # Header parsing is used only to select a verification path. No claim
            # from this unverified token is trusted or used as an identity.
            header = jwt.get_unverified_header(access_token)
            algorithm = header.get("alg")
            if algorithm == "HS256":
                return self._verify_with_auth_server(access_token)
            if algorithm not in self._ASYMMETRIC_ALGORITHMS:
                raise InvalidAccessToken("Unsupported access-token algorithm.")

            signing_key = self.jwks_client.get_signing_key_from_jwt(access_token)
            payload = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=[algorithm],
                issuer=self.config.issuer,
                audience="authenticated",
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
            if payload.get("role") != "authenticated":
                raise InvalidAccessToken("Token is not a user access token.")
            return self._user_id(payload.get("sub"))
        except AuthServiceUnavailable:
            raise
        except InvalidAccessToken:
            raise
        except jwt.PyJWKClientConnectionError as error:
            raise AuthServiceUnavailable("Could not reach Supabase signing keys.") from error
        except jwt.PyJWTError as error:
            raise InvalidAccessToken("Access token could not be verified.") from error
        except (TypeError, ValueError, KeyError) as error:
            raise InvalidAccessToken("Access token could not be verified.") from error

    def _verify_with_auth_server(self, access_token: str) -> UUID:
        """Ask this project to validate HS256 tokens; never verify with the API key."""

        try:
            response = httpx.get(
                self.config.user_url,
                headers={
                    "apikey": self.config.publishable_key,
                    "Authorization": f"Bearer {access_token}",
                },
                timeout=5.0,
            )
        except httpx.RequestError as error:
            raise AuthServiceUnavailable("Could not reach Supabase Auth.") from error

        if response.status_code in {401, 403}:
            raise InvalidAccessToken("Supabase rejected the access token.")
        if response.status_code != 200:
            raise AuthServiceUnavailable("Supabase Auth could not verify the token.")
        try:
            user = response.json()
            if not isinstance(user, dict):
                raise ValueError("Invalid user response")
            return self._user_id(user.get("id"))
        except (ValueError, TypeError) as error:
            raise InvalidAccessToken("Supabase returned an invalid user response.") from error

    @staticmethod
    def _user_id(value: object) -> UUID:
        if not isinstance(value, str):
            raise InvalidAccessToken("Verified token has no user ID.")
        try:
            return UUID(value)
        except ValueError as error:
            raise InvalidAccessToken("Verified token has an invalid user ID.") from error
