from typing import Annotated

from fastapi import APIRouter, Body, Path, Query
from schemas.check_result import CheckResultResponse, Status
from schemas.endpoint import EndpointCreate, EndpointResponse, EndpointUpdate

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


@router.get("/")
async def read_endpoint_list() -> list[EndpointResponse]:
    return []


@router.get("/{endpoint_id}")
async def read_endpoint(endpoint_id: Annotated[int, Path()]) -> EndpointResponse | None:
    return None


@router.post("/", status_code=201)
async def write_endpoint(
    endpoint: Annotated[EndpointCreate, Body()],
) -> EndpointResponse:
    pass


@router.patch("/{endpoint_id}", status_code=204)
async def update_endpoint(
    endpoint_id: Annotated[int, Path()],
    endpoint_entity: Annotated[EndpointUpdate, Path()],
) -> None:
    return


@router.delete("/{endpoint_id}", status_code=204)
async def delete_endpoint(endpoint_id: Annotated[int, Path()]) -> None:
    return


@router.get("/{endpoint_id}/status")
async def read_status(endpiont_id: Annotated[int, Path()]) -> CheckResultResponse:
    pass


@router.get("/{endpoint_id}/history")
async def read_history(
    endpoint_id: Annotated[int, Path()],
    limit: Annotated[int, Query(ge=10, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    filter: Annotated[Status | None, Query()] = None,
) -> list[CheckResultResponse]:
    return []
