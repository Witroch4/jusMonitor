"""Taskiq worker entry point."""

from app.workers.broker import broker

# Import all task modules to register them with the broker
# This ensures tasks are discovered when the worker starts
from app.workers.tasks import chatwit_handlers  # noqa: F401
from app.workers.tasks import peticao_protocolar  # noqa: F401
from app.workers.tasks import tpu_sync  # noqa: F401

# Example of how to create tasks:
# 
# from app.workers.broker import broker
# from app.workers.tasks.base import with_retry, with_timeout, with_rate_limit
# 
# @broker.task
# @with_retry(max_retries=3)
# @with_timeout(30.0)
# async def my_task(arg1: str, arg2: int):
#     # Task implementation
#     pass
#
# To enqueue a task:
# await my_task.kiq(arg1="value", arg2=42)

if __name__ == "__main__":
    # This is used when running the worker directly
    # In production, use: taskiq worker app.workers.main:broker
    import asyncio

    asyncio.run(broker.startup())
