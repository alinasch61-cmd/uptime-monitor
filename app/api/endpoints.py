from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status

from app.core.security import oauth2_scheme
from app.schemas.check_result import CheckResultResponse, Status
from app.schemas.endpoint import EndpointCreate, EndpointResponse, EndpointUpdate

router = APIRouter(
    prefix="/endpoints", tags=["endpoints"], dependencies=[Depends(oauth2_scheme)]
)


@router.get("/", response_model=list[EndpointResponse])
async def read_endpoint_list() -> list[EndpointResponse]:
    return []


@router.get("/{endpoint_id}", response_model=EndpointResponse | None)
async def read_endpoint(
    endpoint_id: Annotated[int, Path()],
) -> EndpointResponse | None:
    return None


@router.post("/", status_code=201, response_model=EndpointResponse)
async def write_endpoint(
    endpoint: Annotated[EndpointCreate, Body()],
) -> EndpointResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This method is not implemented yet",
    )


@router.patch("/{endpoint_id}", status_code=204)
async def update_endpoint(
    endpoint_id: Annotated[int, Path()],
    endpoint_entity: Annotated[EndpointUpdate, Path()],
) -> None:
    return


@router.delete("/{endpoint_id}", status_code=204)
async def delete_endpoint(endpoint_id: Annotated[int, Path()]) -> None:
    return


@router.get("/{endpoint_id}/status", response_model=CheckResultResponse)
async def read_status(endpiont_id: Annotated[int, Path()]) -> CheckResultResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This method is not implemented yet",
    )


@router.get("/{endpoint_id}/history", response_model=list[CheckResultResponse])
async def read_history(
    endpoint_id: Annotated[int, Path()],
    limit: Annotated[int, Query(ge=10, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    filter: Annotated[Status | None, Query()] = None,
) -> list[CheckResultResponse]:
    return []
