"""Aplicação FastAPI: API REST, interface web e inicialização do banco (compatível com Vercel)."""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.seed import ensure_initialized, bootstrap_initial_data  # noqa: F401 (reexportado p/ testes)
from app.api.routes import api_router

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
STATIC_DIR = PUBLIC_DIR / "static"
log = logging.getLogger("campanhas")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_initialized()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)


@app.middleware("http")
async def init_and_headers(request: Request, call_next):
    # Na Vercel o "lifespan" pode não rodar: inicializa no primeiro acesso.
    ensure_initialized()
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Erro não tratado em %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erro interno. A operação não foi concluída; tente novamente."})


app.include_router(api_router)
# Na Vercel, public/ é servido pela CDN; localmente, o próprio FastAPI serve os arquivos.
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def serve_index():
    index = PUBLIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    # Na Vercel, public/ fica na CDN e pode não estar dentro da função.
    return RedirectResponse("/index.html")


@app.get("/health")
def health_check():
    return {"status": "healthy", "app": settings.app_name, "version": settings.app_version,
            "demo_mode": settings.demo_mode, "timestamp": datetime.utcnow().isoformat()}
