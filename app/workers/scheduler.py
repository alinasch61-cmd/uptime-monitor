from apscheduler.schedulers.blocking import (  # type: ignore[import-untyped]
    BlockingScheduler,
)

from app.db.session import SessionLocal
from app.services.endpoint import EndpointRepository
from app.workers.job import run_endpoint_check
from app.workers.queue import queue


def dispatch_checks() -> None:
    with SessionLocal() as session:
        repo = EndpointRepository(session=session)
        endpoints = repo.get_due_list()

        for endpoint in endpoints:
            endpoint.next_check_at = repo.calculate_next_check_time(endpoint)

        session.commit()

        for endpoint in endpoints:
            queue.enqueue(
                run_endpoint_check,
                endpoint.id,
            )


def create_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler()

    scheduler.add_job(
        dispatch_checks, trigger="interval", seconds=120, max_instances=1, coalesce=True
    )

    return scheduler


if __name__ == "__main__":
    scheduler = create_scheduler()

    try:
        scheduler.start()
    except KeyboardInterrupt, SystemExit:
        scheduler.shutdown()
