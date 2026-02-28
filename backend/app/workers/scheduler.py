"""Task scheduler using asyncio for cron-based task execution."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional

from croniter import croniter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.models.worker_schedule import WorkerSchedule

logger = logging.getLogger(__name__)

# Registry of task functions by name
_task_registry: dict[str, Callable] = {}
_scheduler_task: Optional[asyncio.Task] = None


def register_task(task_name: str, func: Callable) -> None:
    """Register a callable task by name."""
    _task_registry[task_name] = func
    logger.info("scheduler_task_registered", extra={"task_name": task_name})


async def trigger_task_now(task_name: str) -> None:
    """Trigger a registered task immediately."""
    func = _task_registry.get(task_name)
    if not func:
        raise ValueError(f"Task '{task_name}' not registered")

    logger.info("scheduler_task_manual_trigger", extra={"task_name": task_name})

    # Update last_run_at
    async with await get_session() as session:
        await session.execute(
            update(WorkerSchedule)
            .where(WorkerSchedule.task_name == task_name)
            .values(last_run_at=datetime.utcnow())
        )
        await session.commit()

    # Run in background
    asyncio.create_task(_run_task(task_name, func))


async def _run_task(task_name: str, func: Callable) -> None:
    """Execute a task with error handling."""
    try:
        logger.info("scheduler_task_running", extra={"task_name": task_name})
        if asyncio.iscoroutinefunction(func):
            await func()
        else:
            func()
        logger.info("scheduler_task_completed", extra={"task_name": task_name})
    except Exception as e:
        logger.error("scheduler_task_failed", extra={
            "task_name": task_name,
            "error": str(e),
        })


def _get_next_run(cron_expression: str, base_time: Optional[datetime] = None) -> datetime:
    """Calculate next run time from a cron expression."""
    base = base_time or datetime.utcnow()
    cron = croniter(cron_expression, base)
    return cron.get_next(datetime)


async def _scheduler_loop() -> None:
    """Main scheduler loop - checks schedules every 30 seconds."""
    logger.info("scheduler_loop_started")

    while True:
        try:
            async with await get_session() as session:
                result = await session.execute(
                    select(WorkerSchedule).where(WorkerSchedule.is_active == True)
                )
                schedules = result.scalars().all()

                now = datetime.utcnow()

                for schedule in schedules:
                    # Calculate next run if not set
                    if not schedule.next_run_at:
                        schedule.next_run_at = _get_next_run(schedule.cron_expression)
                        await session.flush()

                    # Check if it's time to run
                    if schedule.next_run_at and now >= schedule.next_run_at:
                        func = _task_registry.get(schedule.task_name)
                        if func:
                            asyncio.create_task(_run_task(schedule.task_name, func))

                            schedule.last_run_at = now
                            schedule.next_run_at = _get_next_run(schedule.cron_expression, now)
                            await session.flush()
                        else:
                            logger.warning("scheduler_task_not_registered", extra={
                                "task_name": schedule.task_name,
                            })

                await session.commit()

        except Exception as e:
            logger.error("scheduler_loop_error", extra={"error": str(e)})

        await asyncio.sleep(30)


async def start_scheduler() -> None:
    """Start the scheduler background loop."""
    global _scheduler_task

    # Register known tasks from workers
    _register_default_tasks()

    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("scheduler_started")


async def stop_scheduler() -> None:
    """Stop the scheduler background loop."""
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
        logger.info("scheduler_stopped")


def _register_default_tasks() -> None:
    """Register default tasks from worker modules."""
    try:
        from app.workers.tasks.datajud_poller import poll_datajud_for_all_tenants
        register_task("datajud_poller", poll_datajud_for_all_tenants)
    except ImportError:
        logger.warning("Could not import datajud_poller task")

    try:
        from app.workers.tasks.lead_scoring import score_all_tenant_leads_task
        register_task("lead_scoring", score_all_tenant_leads_task)
    except ImportError:
        logger.warning("Could not import lead_scoring task")

    try:
        from app.workers.tasks.embeddings import batch_generate_embeddings_for_tenant
        register_task("embeddings_batch", batch_generate_embeddings_for_tenant)
    except ImportError:
        logger.warning("Could not import embeddings task")
