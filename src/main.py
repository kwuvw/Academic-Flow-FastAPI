from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.auth.router import router as auth_router
from src.config import settings
from src.frontend.router import router as frontend_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
)

app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")

app.include_router(frontend_router)
app.include_router(auth_router)
