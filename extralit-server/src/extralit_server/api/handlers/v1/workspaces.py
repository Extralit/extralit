from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import WorkspacePolicy, WorkspaceUserPolicy, authorize
from extralit_server.api.schemas.v1.users import User as UserSchema
from extralit_server.api.schemas.v1.users import Users
from extralit_server.api.schemas.v1.workspaces import (
    Workspace as WorkspaceSchema,
)
from extralit_server.api.schemas.v1.workspaces import (
    WorkspaceCreate,
    WorkspaceDoctorCheckResult,
    WorkspaceDoctorResponse,
    Workspaces,
    WorkspaceUserCreate,
)
from extralit_server.contexts import accounts, files
from extralit_server.database import get_async_db
from extralit_server.errors.future import NotFoundError, NotUniqueError, UnprocessableEntityError
from extralit_server.models import Dataset, User, Workspace, WorkspaceUser
from extralit_server.search_engine import get_search_engine
from extralit_server.security import auth
from extralit_server.settings import settings

router = APIRouter(tags=["workspaces"])


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceSchema)
async def get_workspace(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    return await Workspace.get_or_raise(db, workspace_id)


@router.post("/workspaces", status_code=status.HTTP_201_CREATED, response_model=WorkspaceSchema)
async def create_workspace(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_create: WorkspaceCreate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, WorkspacePolicy.create)

    try:
        workspace = await accounts.create_workspace(db, workspace_create.model_dump())
    except NotUniqueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return workspace


@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceSchema)
async def delete_workspace(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
    storage=Depends(files.get_storage),
):
    await authorize(current_user, WorkspacePolicy.delete)

    try:
        workspace = await Workspace.get_or_raise(db, workspace_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        await files.delete_workspace_objects(storage, workspace.name)
    except Exception as e:
        # Log the error but continue with workspace deletion
        print(f"Error deleting objects for workspace {workspace.name}: {e!s}")

    try:
        return await accounts.delete_workspace(db, workspace)
    except NotUniqueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        # Handle any other unexpected errors
        print(f"Error deleting workspace {workspace.id}: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting workspace: {e!s}"
        )


@router.get("/me/workspaces")
async def list_workspaces_me(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
) -> Workspaces:
    await authorize(current_user, WorkspacePolicy.list_workspaces_me)

    if current_user.is_owner:
        workspaces = await accounts.list_workspaces(db)
    else:
        workspaces = await accounts.list_workspaces_by_user_id(db, current_user.id)

    return Workspaces(items=workspaces)


@router.get("/workspaces/{workspace_id}/users", response_model=Users)
async def list_workspace_users(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, WorkspaceUserPolicy.list(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)

    await workspace.awaitable_attrs.users

    return Users(items=workspace.users)


@router.post("/workspaces/{workspace_id}/users", status_code=status.HTTP_201_CREATED, response_model=UserSchema)
async def create_workspace_user(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    workspace_user_create: WorkspaceUserCreate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, WorkspaceUserPolicy.create)

    workspace = await Workspace.get_or_raise(db, workspace_id)

    try:
        user = await User.get_or_raise(db, workspace_user_create.user_id)
    except NotFoundError as e:
        raise UnprocessableEntityError(e.message)

    workspace_user = await accounts.create_workspace_user(db, {"workspace_id": workspace.id, "user_id": user.id})

    return workspace_user.user


@router.delete("/workspaces/{workspace_id}/users/{user_id}", response_model=UserSchema)
async def delete_workspace_user(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    user_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    workspace_user = await WorkspaceUser.get_by_or_raise(db, workspace_id=workspace_id, user_id=user_id)

    await authorize(current_user, WorkspaceUserPolicy.delete(workspace_user))

    await accounts.delete_workspace_user(db, workspace_user)

    return await workspace_user.awaitable_attrs.user


@router.post("/workspaces/{workspace_id}/doctor", response_model=WorkspaceDoctorResponse)
async def workspace_doctor(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
    storage=Depends(files.get_storage),
    autofix: bool = True,
):
    """
    Run diagnostics on a workspace and optionally auto-fix issues.

    Checks:
    - Storage root is reachable (informational)
    - RQ worker pool connectivity (informational)
    """
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)
    checks = []

    # Check 1: storage root reachable. A workspace is a prefix under it, so there is nothing
    # per-workspace to create or fix.
    if await storage.healthy():
        checks.append(
            WorkspaceDoctorCheckResult(
                check_name="storage",
                status="ok",
                message=f"Storage root '{settings.storage_url}' is reachable",
                fixed=False,
            )
        )
    else:
        checks.append(
            WorkspaceDoctorCheckResult(
                check_name="storage",
                status="error",
                message=f"Storage root '{settings.storage_url}' is not reachable",
                fixed=False,
            )
        )

    # Check 2: RQ worker pool connectivity
    try:
        from extralit_server.jobs.queues import DEFAULT_QUEUE

        # Try to ping Redis through the queue connection
        connection = DEFAULT_QUEUE.connection
        connection.ping()

        checks.append(
            WorkspaceDoctorCheckResult(
                check_name="rq_worker_pool",
                status="ok",
                message="Redis Queue worker pool is reachable",
                fixed=False,
            )
        )
    except Exception as e:
        checks.append(
            WorkspaceDoctorCheckResult(
                check_name="rq_worker_pool",
                status="warning",
                message=f"Could not connect to RQ worker pool: {e!s}",
                fixed=False,
            )
        )

    # Check 3: Elasticsearch indexes for datasets (informational only)
    try:
        # Get datasets for this workspace
        from sqlalchemy import select

        result = await db.execute(select(Dataset).where(Dataset.workspace_id == workspace.id))
        datasets = result.scalars().all()

        if datasets:
            async with get_search_engine() as search_engine:
                missing_indexes = []
                for dataset in datasets:
                    index_name = f"ex.{dataset.id}"
                    index_exists = await search_engine._index_exists_request(index_name)
                    if not index_exists:
                        missing_indexes.append(dataset.name)

                if missing_indexes:
                    checks.append(
                        WorkspaceDoctorCheckResult(
                            check_name="elasticsearch_indexes",
                            status="warning",
                            message=f"Missing Elasticsearch indexes for {len(missing_indexes)} dataset(s): {', '.join(missing_indexes[:3])}{'...' if len(missing_indexes) > 3 else ''}",
                            fixed=False,
                        )
                    )
                else:
                    checks.append(
                        WorkspaceDoctorCheckResult(
                            check_name="elasticsearch_indexes",
                            status="ok",
                            message=f"All {len(datasets)} dataset(s) have Elasticsearch indexes",
                            fixed=False,
                        )
                    )
        else:
            checks.append(
                WorkspaceDoctorCheckResult(
                    check_name="elasticsearch_indexes",
                    status="ok",
                    message="No datasets found for this workspace",
                    fixed=False,
                )
            )
    except Exception as e:
        checks.append(
            WorkspaceDoctorCheckResult(
                check_name="elasticsearch_indexes",
                status="warning",
                message=f"Could not check Elasticsearch indexes: {e!s}",
                fixed=False,
            )
        )

    # Check 5: Database connections health with autofix
    try:
        import asyncio

        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError

        # Import the async engine to access database URL and dispose method
        from extralit_server.database import async_engine

        # Get database URL and detect type
        db_url = str(async_engine.url)
        is_postgresql = "postgresql" in db_url.lower()
        is_sqlite = "sqlite" in db_url.lower()

        async def check_db_health():
            if is_postgresql:
                # A. Liveness Check (The most important part)
                # Simple query to prove the TCP pipe is open.
                await db.execute(text("SELECT 1"))

                # B. Deep Inspection (Optional - only if Liveness passes)
                active_connections_query = text("""
                    SELECT
                        count(*) as active_connections,
                        count(*) filter (where state = 'idle in transaction' and now() - state_change > interval '1 minute') as stale_transaction_connections
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """)

                result = await db.execute(active_connections_query)
                conn_stats = result.first()

                if conn_stats:
                    stale_txn = conn_stats.stale_transaction_connections
                    active = conn_stats.active_connections

                    if stale_txn > 0:
                        # Idle in transaction is BAD. It blocks table locks.
                        checks.append(
                            WorkspaceDoctorCheckResult(
                                check_name="db_transaction_health",
                                status="warning",
                                message=f"Found {stale_txn} connections idle in transaction.",
                            )
                        )
                    else:
                        checks.append(
                            WorkspaceDoctorCheckResult(
                                check_name="db_connection_health",
                                status="ok",
                                message=f"Pool healthy. Active DB sessions: {active}",
                            )
                        )

            elif is_sqlite:
                # SQLite doesn't have connection pooling like PostgreSQL
                # Just check if we can execute a simple query
                simple_query = text("SELECT 1 as test")
                result = await db.execute(simple_query)
                test_result = result.scalar()

                if test_result == 1:
                    checks.append(
                        WorkspaceDoctorCheckResult(
                            check_name="database_connections",
                            status="ok",
                            message="SQLite database connection is healthy (SQLite uses file-based connections, no pooling)",
                            fixed=False,
                        )
                    )
                else:
                    checks.append(
                        WorkspaceDoctorCheckResult(
                            check_name="database_connections",
                            status="error",
                            message="SQLite database connection test failed",
                            fixed=False,
                        )
                    )
            else:
                # Other database types - skip detailed connection monitoring
                checks.append(
                    WorkspaceDoctorCheckResult(
                        check_name="database_connections",
                        status="ok",
                        message=f"Database connection check skipped for {db_url.split('://')[0]} (unsupported for detailed monitoring)",
                        fixed=False,
                    )
                )

        # SAFETY TIMEOUT: If DB doesn't answer in 3s, the connection is dead.
        # This prevents the doctor check from hanging for 15 mins.
        await asyncio.wait_for(check_db_health(), timeout=3.0)

    except (asyncio.TimeoutError, SQLAlchemyError, OSError) as e:
        # Handle database connectivity issues
        if autofix:
            # THE AUTOFIX LOGIC
            # If we timed out or got a connection error, the pool is likely stale.

            error_msg = f"Database unresponsive (Timeout/Error). Resetting connection pool. Error: {e!s}"

            # DISPOSE THE POOL
            # This closes all internal sockets. The next request will force a fresh handshake.
            try:
                await async_engine.dispose()
                checks.append(
                    WorkspaceDoctorCheckResult(
                        check_name="database_connections",
                        status="warning",  # Warning because we had to reset
                        message=error_msg,
                        fixed=True,  # We successfully reset the pool
                    )
                )
            except Exception as dispose_error:
                error_msg += f" (Failed to dispose pool: {dispose_error!s})"
                checks.append(
                    WorkspaceDoctorCheckResult(
                        check_name="database_connections",
                        status="error",
                        message=error_msg,
                        fixed=False,
                    )
                )
        else:
            # Just report the issue without fixing
            checks.append(
                WorkspaceDoctorCheckResult(
                    check_name="database_connections",
                    status="error",
                    message=f"Database unresponsive (Timeout/Error). Run with --autofix to automatically reset connection pool. Error: {e!s}",
                    fixed=False,
                )
            )
    except Exception as e:
        checks.append(
            WorkspaceDoctorCheckResult(
                check_name="database_connections",
                status="warning",
                message=f"Could not check database connections: {e!s}",
                fixed=False,
            )
        )

    # Determine overall status
    has_errors = any(check.status == "error" for check in checks)
    has_fixed = any(check.fixed for check in checks)
    has_warnings = any(check.status == "warning" for check in checks)

    if has_errors:
        overall_status = "issues_found"
    elif has_fixed:
        overall_status = "issues_fixed"
    elif has_warnings:
        overall_status = "issues_found"
    else:
        overall_status = "healthy"

    return WorkspaceDoctorResponse(
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        checks=checks,
        overall_status=overall_status,
    )
