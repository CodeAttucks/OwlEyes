import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .secrets import SecretError, get_bool_secret, get_required_secret, get_secret

bearer_scheme = HTTPBearer()

_OPENID_CACHE: dict[str, Any] = {"data": None, "expires_at": 0.0}


def _is_auth_enabled() -> bool:
    try:
        return get_bool_secret("AUTH_ENABLED", default=False)
    except SecretError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _tenant_id() -> str:
    try:
        return get_required_secret("AZURE_AD_TENANT_ID")
    except SecretError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _client_id() -> str:
    try:
        return get_required_secret("AZURE_AD_CLIENT_ID")
    except SecretError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _issuer() -> str:
    explicit_issuer = get_secret("AZURE_AD_ISSUER", "")
    if explicit_issuer:
        return explicit_issuer
    tenant = _tenant_id()
    return f"https://login.microsoftonline.com/{tenant}/v2.0"


def _audience() -> str:
    explicit_aud = get_secret("AZURE_AD_AUDIENCE", "")
    if explicit_aud:
        return explicit_aud
    return _client_id()


def _openid_config_url() -> str:
    explicit_url = get_secret("AZURE_AD_OPENID_CONFIG_URL", "")
    if explicit_url:
        return explicit_url
    tenant = _tenant_id()
    return f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"


async def _openid_config() -> dict[str, Any]:
    now = time.time()
    if _OPENID_CACHE["data"] and now < float(_OPENID_CACHE["expires_at"]):
        return _OPENID_CACHE["data"]

    url = _openid_config_url()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load Azure AD OpenID config: {exc}") from exc

    _OPENID_CACHE["data"] = data
    _OPENID_CACHE["expires_at"] = now + 3600
    return data


async def _find_signing_key(token: str) -> dict[str, Any]:
    try:
        token_header = jwt.get_unverified_header(token)
        token_kid = token_header.get("kid")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid JWT header") from exc

    if not token_kid:
        raise HTTPException(status_code=401, detail="JWT missing kid")

    openid = await _openid_config()
    jwks_uri = openid.get("jwks_uri")
    if not jwks_uri:
        raise HTTPException(status_code=502, detail="OpenID config missing jwks_uri")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            jwks_response = await client.get(jwks_uri)
            jwks_response.raise_for_status()
            jwks = jwks_response.json().get("keys", [])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load JWKS keys: {exc}") from exc

    for key in jwks:
        if key.get("kid") == token_kid:
            return key

    raise HTTPException(status_code=401, detail="Signing key not found for token")


async def require_auth_if_enabled(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any] | None:
    if not _is_auth_enabled():
        return None

    token = credentials.credentials
    signing_key = await _find_signing_key(token)

    try:
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=_audience(),
            issuer=_issuer(),
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {exc}") from exc

    return claims
