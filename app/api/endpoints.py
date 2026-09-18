from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.security import oauth2_scheme
from app.db.session import get_db
from app.models.endpoint import Endpoint as EndpointModel
from app.models.user import User
from app.schemas.check_result import CheckResultResponse, Status
from app.schemas.endpoint import EndpointCreate, EndpointResponse, EndpointUpdate
from app.services.auth import get_current_user
from app.services.endpoint import EndpointExistError, EndpointRepository


def require_authenticated_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_user = get_current_user(token, db)
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return current_user


def get_endpoint_service(db: Annotated[Session, Depends(get_db)]):
    return EndpointRepository(db)


router = APIRouter(
    prefix="/endpoints",
    tags=["endpoints"],
    dependencies=[Depends(require_authenticated_user)],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Could not validate credentials"},
    },
)


@router.get("/", response_model=list[EndpointResponse])
def read_endpoint_list(
    user: Annotated[User, Depends(require_authenticated_user)],
    endpoint_service: Annotated[EndpointRepository, Depends(get_endpoint_service)],
) -> Sequence[EndpointResponse]:
    endpoint_collection = endpoint_service.get_list(user_id=user.id)
    return [
        EndpointResponse.model_validate(endpoint) for endpoint in endpoint_collection
    ]


@router.get(
    "/{endpoint_id}",
    response_model=EndpointResponse | None,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Endpoint not found"}},
)
def read_endpoint(
    endpoint_id: Annotated[int, Path()],
    user: Annotated[User, Depends(require_authenticated_user)],
    endpoint_service: Annotated[EndpointRepository, Depends(get_endpoint_service)],
) -> EndpointResponse | None:
    endpoint = endpoint_service.get(endpoint_id, user.id)

    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found"
        )

    return EndpointResponse.model_validate(endpoint)


@router.post(
    "/",
    status_code=201,
    response_model=EndpointResponse,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Endpoint with this URL and status code already exists"
        }
    },
)
def write_endpoint(
    endpoint: Annotated[EndpointCreate, Body()],
    user: Annotated[User, Depends(require_authenticated_user)],
    endpoint_service: Annotated[EndpointRepository, Depends(get_endpoint_service)],
) -> EndpointResponse:
    endpoint_model = EndpointModel(
        user_id=user.id,
        url=endpoint.url,
        expected_status_code=endpoint.expected_status_code,
        check_frequency_seconds=endpoint.check_frequency_seconds,
        is_paused=endpoint.is_paused,
    )

    try:
        new_endpoint = endpoint_service.create(endpoint_model)
    except EndpointExistError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Endpoint with this URL and status code already exists",
        )

    return EndpointResponse.model_validate(new_endpoint)


@router.patch(
    "/{endpoint_id}",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Endpoint not found"},
    },
)
def update_endpoint(
    endpoint_id: Annotated[int, Path()],
    new_vals: Annotated[EndpointUpdate, Body()],
    user: Annotated[User, Depends(require_authenticated_user)],
    endpoint_service: Annotated[EndpointRepository, Depends(get_endpoint_service)],
) -> EndpointResponse:
    endpoint = endpoint_service.get(endpoint_id, user.id)

    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found"
        )

    if new_vals.check_frequency_seconds is not None:
        endpoint.check_frequency_seconds = new_vals.check_frequency_seconds

    if new_vals.is_paused is not None:
        endpoint.is_paused = new_vals.is_paused

    updated_endpoint = endpoint_service.patch(endpoint)
    return EndpointResponse.model_validate(updated_endpoint)


@router.delete(
    "/{endpoint_id}",
    status_code=204,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Endpoint not found"}},
)
def delete_endpoint(
    endpoint_id: Annotated[int, Path()],
    user: Annotated[User, Depends(require_authenticated_user)],
    endpoint_service: Annotated[EndpointRepository, Depends(get_endpoint_service)],
) -> None:
    endpoint = endpoint_service.get(endpoint_id, user.id)

    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found"
        )

    endpoint_service.delete(endpoint)


@router.get("/{endpoint_id}/status", response_model=CheckResultResponse)
def read_status(endpoint_id: Annotated[int, Path()]) -> CheckResultResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This method is not implemented yet",
    )


@router.get("/{endpoint_id}/history", response_model=list[CheckResultResponse])
def read_history(
    endpoint_id: Annotated[int, Path()],
    limit: Annotated[int, Query(ge=10, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    filter: Annotated[Status | None, Query()] = None,
) -> list[CheckResultResponse]:
    return []
