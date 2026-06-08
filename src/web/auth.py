"""Web authentication using shared CLI tokens.

WEB-03: Web app authenticates using shared CLI tokens (data/tokens.json).
"""

from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..auth.oauth import load_tokens


# Security scheme for OpenAPI
security = HTTPBearer(auto_error=False)


class UserContext:
    """User context for authenticated requests."""

    def __init__(self, authenticated: bool = False, username: Optional[str] = None):
        self.authenticated = authenticated
        self.username = username


async def get_current_user(
    request: Request,
    token_path: Optional[Path] = None,
) -> UserContext:
    """Get the current user from shared CLI tokens.

    This dependency loads tokens from data/tokens.json and returns
    a UserContext. If tokens don't exist, returns unauthenticated context.

    Args:
        request: FastAPI request object.
        token_path: Optional path to token file. Defaults to data/tokens.json.

    Returns:
        UserContext with authentication status.
    """
    if token_path is None:
        token_path = Path("data/tokens.json")

    tokens = load_tokens(token_path)

    if tokens is None:
        return UserContext(authenticated=False)

    access_token, _ = tokens

    # Verify token is valid by making a test API call
    # For simplicity, we'll just check the token exists
    # A more robust implementation would verify with X API

    return UserContext(authenticated=True)


async def require_auth(
    user: UserContext = Depends(get_current_user),
) -> UserContext:
    """Require authentication for protected routes.

    Args:
        user: UserContext from get_current_user dependency.

    Returns:
        UserContext if authenticated.

    Raises:
        HTTPException: If not authenticated (401).
    """
    if not user.authenticated:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Run 'xbm auth' first.",
        )
    return user


__all__ = ["UserContext", "get_current_user", "require_auth"]