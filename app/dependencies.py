from enum import Enum
from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db

__all__ = ["get_db", "require_player", "require_moderator", "require_admin", "KeyScope"]


class KeyScope(str, Enum):
    PLAYER = "PLAYER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


def _resolve_scope(api_key: str) -> KeyScope | None:
    settings = get_settings()
    if api_key in settings.get_admin_keys():
        return KeyScope.ADMIN
    if api_key in settings.get_moderator_keys():
        return KeyScope.MODERATOR
    if api_key in settings.get_player_keys():
        return KeyScope.PLAYER
    return None


def _auth(x_api_key: str | None, required_scope: KeyScope) -> KeyScope:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "UNAUTHORIZED", "message": "Missing X-API-Key header"})

    scope = _resolve_scope(x_api_key)
    if scope is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "UNAUTHORIZED", "message": "Invalid API key"})

    scope_order = {KeyScope.PLAYER: 0, KeyScope.MODERATOR: 1, KeyScope.ADMIN: 2}
    if scope_order[scope] < scope_order[required_scope]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "FORBIDDEN", "message": "Insufficient scope"})

    return scope


def require_player(x_api_key: str | None = Header(default=None)) -> KeyScope:
    return _auth(x_api_key, KeyScope.PLAYER)


def require_moderator(x_api_key: str | None = Header(default=None)) -> KeyScope:
    return _auth(x_api_key, KeyScope.MODERATOR)


def require_admin(x_api_key: str | None = Header(default=None)) -> KeyScope:
    return _auth(x_api_key, KeyScope.ADMIN)
