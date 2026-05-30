from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from src.auth.router import router as auth_router
from src.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG
)

app.mount("/static", StaticFiles(directory="src/frontend/static"), name = "static")
templates = Jinja2Templates(directory="src/frontend/templates")


@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(
        name = "index.html",
        context = {"request": request, "title": "Academic Flow | Главная"}
    )
    
    
app.include_router(auth_router)
@app.get("/")
def home():
    return {"status": "API is running"}