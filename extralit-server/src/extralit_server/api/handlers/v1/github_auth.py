"""
GitHub Device Flow authentication endpoints for Copilot integration.

The device_code secret is kept server-side; only the user_code and
verification_uri are returned to the browser.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from extralit_server.models import User
from extralit_server.security import auth
from extralit_server.utils.auth_helpers import (
    clear_pending_flow,
    clear_token,
    get_pending_flow,
    initiate_device_flow,
    is_authenticated,
    poll_for_token,
    save_token,
    store_pending_flow,
)

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


# ── Response models ──────────────────────────────────────────────────


class AuthStatusResponse(BaseModel):
    authenticated: bool
    username: str


class DeviceFlowResponse(BaseModel):
    """Returned to the browser - no device_code."""

    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


class PollTokenResponse(BaseModel):
    status: str  # "pending" | "slow_down" | "authorized" | "error"
    message: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/auth/github/status")
async def get_auth_status(
    current_user: User = Depends(auth.get_current_user),
) -> AuthStatusResponse:
    """Check whether the current user has a valid GitHub Copilot token."""
    return AuthStatusResponse(
        authenticated=is_authenticated(current_user.username),
        username=current_user.username,
    )


@router.post("/auth/github/login")
async def initiate_github_login(
    current_user: User = Depends(auth.get_current_user),
) -> DeviceFlowResponse:
    """Start the GitHub OAuth device flow.

    Returns only the user_code and verification_uri.  The device_code
    is stored server-side and used automatically by the /poll endpoint.
    """
    try:
        flow_data = await initiate_device_flow()
    except Exception:
        _LOGGER.exception("Failed to initiate GitHub Device Flow for %s", current_user.username)
        raise HTTPException(status_code=502, detail="Failed to contact GitHub for device-code flow")

    # Keep the device_code on the server
    store_pending_flow(current_user.username, flow_data)
    _LOGGER.info("Initiated GitHub Device Flow for %s", current_user.username)

    return DeviceFlowResponse(
        user_code=flow_data["user_code"],
        verification_uri=flow_data["verification_uri"],
        expires_in=flow_data["expires_in"],
        interval=flow_data["interval"],
    )


@router.post("/auth/github/poll")
async def poll_github_token(
    current_user: User = Depends(auth.get_current_user),
) -> PollTokenResponse:
    """Poll for the access token after the user authorises on GitHub.

    The client does not need to send a device_code — it is stored
    server-side from the /login step.
    """
    flow = get_pending_flow(current_user.username)
    if flow is None:
        raise HTTPException(
            status_code=400,
            detail="No pending device flow. Call /auth/github/login first.",
        )

    try:
        token_data = await poll_for_token(device_code=flow["device_code"])
        save_token(current_user.username, token_data)
        clear_pending_flow(current_user.username)
        _LOGGER.info("GitHub token saved for %s", current_user.username)
        return PollTokenResponse(status="authorized", message="Successfully authenticated with GitHub")

    except TimeoutError as exc:
        # "slow_down" tells the frontend to increase its polling interval
        status = "slow_down" if str(exc) == "slow_down" else "pending"
        return PollTokenResponse(status=status, message="Authorization pending")

    except ValueError as exc:
        _LOGGER.warning("Token polling failed for %s: %s", current_user.username, exc)
        clear_pending_flow(current_user.username)
        return PollTokenResponse(status="error", message="Authorization failed or expired. Please try again.")


@router.delete("/auth/github/logout")
async def logout_github(
    current_user: User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Clear the stored GitHub token."""
    clear_token(current_user.username)
    clear_pending_flow(current_user.username)
    _LOGGER.info("Logged out GitHub for %s", current_user.username)
    return {"message": "Successfully logged out from GitHub"}
