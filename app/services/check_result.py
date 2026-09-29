from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult as CheckResultModel
from app.models.check_result import Status as CheckResultStatus


class CheckResultRepository:
    def __init__(self, session: Session):
        self.db = session

    def create(self, check_result: CheckResultModel) -> None:
        self.db.add(check_result)
        self.db.commit()

    def get_latest(self, endpoint_id: int) -> CheckResultModel | None:
        stmt = (
            select(CheckResultModel)
            .where(CheckResultModel.endpoint_id == endpoint_id)
            .order_by(CheckResultModel.checked_at.desc(), CheckResultModel.id.desc())
            .limit(1)
        )

        return self.db.scalars(stmt).first()

    def get_list(
        self,
        endpoint_id: int,
        limit: int,
        offset: int,
        filter: CheckResultStatus | None,
    ) -> Sequence[CheckResultModel]:
        stmt = select(CheckResultModel).where(
            CheckResultModel.endpoint_id == endpoint_id
        )

        if filter is not None:
            stmt = stmt.where(CheckResultModel.result_status == filter)

        stmt = (
            stmt.order_by(
                CheckResultModel.checked_at.desc(), CheckResultModel.id.desc()
            )
            .limit(limit=limit)
            .offset(offset=offset)
        )
        return self.db.scalars(stmt).all()
