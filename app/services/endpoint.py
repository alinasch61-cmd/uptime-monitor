from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.endpoint import Endpoint as EndpointModel

_UNIQUE_VIOLATION_SQLSTATE = "23505"


class EndpointExistError(Exception):
    pass


class EndpointRepository:
    def __init__(self, session: Session):
        self.db = session

    def create(self, endpoint: EndpointModel) -> EndpointModel:
        try:
            self.db.add(endpoint)
            self.db.commit()
            self.db.refresh(endpoint)
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == _UNIQUE_VIOLATION_SQLSTATE:
                raise EndpointExistError(
                    "An endpoint with this url and status already exists"
                )

            raise

        return endpoint

    def patch(self, endpoint: EndpointModel) -> EndpointModel:
        self.db.commit()
        self.db.refresh(endpoint)

        return endpoint

    def get(self, endpoint_id: int, user_id: int) -> EndpointModel | None:
        stmt = select(EndpointModel).where(
            EndpointModel.id == endpoint_id, EndpointModel.user_id == user_id
        )
        return self.db.scalars(stmt).first()

    def get_list(self, user_id: int) -> Sequence[EndpointModel]:
        stmt = (
            select(EndpointModel)
            .where(EndpointModel.user_id == user_id)
            .order_by(EndpointModel.id)
        )
        return self.db.scalars(stmt).all()

    def delete(self, endpoint: EndpointModel) -> None:
        self.db.delete(endpoint)
        self.db.commit()
