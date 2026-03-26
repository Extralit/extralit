# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
GitHub authentication endpoints for Copilot integration.
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from extralit_server.models import User
from extralit_server.security import auth
from extralit_server.utils.auth_helpers import GitHubDeviceFlowAuth

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


class AuthStatusResponse(BaseModel):
    """Response model for auth status check."""

    authenticated: bool
    username: str


class DeviceFlowResponse(BaseModel):
    """Response model for device flow initiation."""

    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


@router.get("/auth/github/status")
async def get_auth_status(current_user: User = Depends(auth.get_current_user)) -> AuthStatusResponse:
    """
    Check if the current user has authenticated with GitHub for Copilot access.

    Returns:
        AuthStatusResponse with authentication status and username
    """
    github_auth = GitHubDeviceFlowAuth(username=current_user.username)
    is_authenticated = github_auth.is_authenticated()

    _LOGGER.info(f"Auth status check for {current_user.username}: {is_authenticated}")

    return AuthStatusResponse(
        authenticated=is_authenticated,
        username=current_user.username,
    )


@router.post("/auth/github/login")
async def initiate_github_login(current_user: User = Depends(auth.get_current_user)) -> DeviceFlowResponse:
    """
    Initiate GitHub Device Flow authentication.

    This endpoint starts the OAuth Device Flow and returns the user code
    and verification URI that the user should visit to authorize the application.

    Returns:
        DeviceFlowResponse with device_code, user_code, verification_uri, expires_in, and interval

    Raises:
        ValueError: If GitHub client ID is not configured
    """
    github_auth = GitHubDeviceFlowAuth(username=current_user.username)

    try:
        flow_data = await github_auth.initiate_flow()
        _LOGGER.info(f"Initiated GitHub Device Flow for {current_user.username}")

        # Return device_code so the client can use it to poll for the token
        return DeviceFlowResponse(
            device_code=flow_data["device_code"],
            user_code=flow_data["user_code"],
            verification_uri=flow_data["verification_uri"],
            expires_in=flow_data["expires_in"],
            interval=flow_data["interval"],
        )
    except ValueError as e:
        _LOGGER.error(f"Failed to initiate GitHub Device Flow: {e}")
        raise


class PollTokenRequest(BaseModel):
    """Request model for polling token."""

    device_code: str


class PollTokenResponse(BaseModel):
    """Response model for polling token."""

    status: str  # "pending", "authorized", "error"
    message: str | None = None


@router.post("/auth/github/poll")
async def poll_github_token(
    request: PollTokenRequest,
    current_user: User = Depends(auth.get_current_user),
) -> PollTokenResponse:
    """
    Poll for GitHub access token after user authorization.

    This endpoint should be called by the client after the user has visited
    the verification URI and entered their code.

    Args:
        request: Contains the device_code from the login initiation

    Returns:
        PollTokenResponse indicating status of authorization

    Raises:
        ValueError: If authorization fails or expires
    """
    github_auth = GitHubDeviceFlowAuth(username=current_user.username)

    try:
        # Poll with a short timeout (single attempt)
        token_data = await github_auth.poll_for_token(
            device_code=request.device_code,
            interval=5,
            timeout=10,  # Just one quick check
        )

        # Save the token
        github_auth.save_token(token_data)

        _LOGGER.info(f"Successfully authorized and saved token for {current_user.username}")

        return PollTokenResponse(
            status="authorized",
            message="Successfully authenticated with GitHub",
        )
    except TimeoutError:
        # User hasn't authorized yet
        return PollTokenResponse(
            status="pending",
            message="Authorization pending",
        )
    except ValueError as e:
        _LOGGER.error(f"Token polling error for {current_user.username}: {e}")
        return PollTokenResponse(
            status="error",
            message=str(e),
        )


@router.delete("/auth/github/logout")
async def logout_github(current_user: User = Depends(auth.get_current_user)) -> dict[str, str]:
    """
    Clear the stored GitHub token for the current user.

    Returns:
        Success message
    """
    github_auth = GitHubDeviceFlowAuth(username=current_user.username)
    github_auth.clear_token()

    _LOGGER.info(f"Logged out GitHub for {current_user.username}")

    return {"message": "Successfully logged out from GitHub"}
