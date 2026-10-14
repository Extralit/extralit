import asyncio

from sqlalchemy import orm
from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker

task: asyncio.Task | None = None


def set_task(t: asyncio.Task):
    global task
    task = t


def get_task() -> asyncio.Task:
    return task


TestSession = async_scoped_session(async_sessionmaker(expire_on_commit=False, future=True), get_task)
SyncTestSession = orm.scoped_session(orm.sessionmaker(class_=orm.Session, expire_on_commit=False))
