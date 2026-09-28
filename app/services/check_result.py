from sqlalchemy.orm import Session

from app.models.check_result import CheckResult as CheckResultModel


class CheckResultRepository:
    def __init__(self, session: Session):
        self.db = session

    def create(self, check_result: CheckResultModel) -> None:
        self.db.add(check_result)
        self.db.commit()
