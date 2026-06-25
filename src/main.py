import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.admin.router import router as admin_router
from src.auth.connections_router import router as connections_router
from src.auth.router import router as auth_router
from src.config import settings
from src.database import async_session_maker
from src.frontend.router import router as frontend_router
from src.tasks.models import Task
from src.tasks.router import router as tasks_router

logger = logging.getLogger(__name__)


async def cleanup_expired_tasks():
    """
    Фоновая задача: удаление заданий, у которых deadline < (текущая_дата - 7 дней).
    Запускается при старте приложения и повторяется каждый час.
    """
    while True:
        try:
            from datetime import datetime, timedelta, timezone

            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(days=7)

            async with async_session_maker() as session:
                from sqlalchemy import select

                query = select(Task).where(Task.deadline < cutoff)
                result = await session.execute(query)
                expired_tasks = list(result.scalars().all())

                if expired_tasks:
                    deleted_count = 0
                    for task in expired_tasks:
                        # Удаляем файлы задания с диска
                        if task.file_paths:
                            try:
                                paths = json.loads(task.file_paths)
                                for p in paths:
                                    full_path = os.path.join("src", "frontend", p.lstrip("/"))
                                    if os.path.exists(full_path):
                                        os.remove(full_path)
                            except (json.JSONDecodeError, TypeError, OSError):
                                pass
                        await session.delete(task)
                        deleted_count += 1

                    await session.commit()
                    logger.info(f"[Cleanup] Удалено просроченных заданий: {deleted_count}")
                else:
                    logger.debug("[Cleanup] Просроченных заданий для удаления нет")
        except Exception as e:
            logger.error(f"[Cleanup] Ошибка при очистке заданий: {e}")

        # Повторяем каждый час
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте приложения запускаем фоновую задачу очистки
    task = asyncio.create_task(cleanup_expired_tasks())
    yield
    # При остановке отменяем фоновую задачу
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")

app.include_router(frontend_router)
app.include_router(auth_router)
app.include_router(connections_router)
app.include_router(tasks_router)
app.include_router(admin_router)
