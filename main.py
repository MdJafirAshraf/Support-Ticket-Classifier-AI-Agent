import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from core.config import get_settings
from core.logging_config import configure_logging, get_logger
from middleware.request_logging import RequestLoggingMiddleware
from middleware.error_handler import register_error_handlers
from database import Base, engine
from routers import tickets, web

from core.tracing import configure_tracing
configure_tracing() 

configure_logging()
logger = get_logger("main")
settings = get_settings()

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    logger.info(f"{settings.app_name} started — tables ensured, model={settings.classifier_model}")

    yield

    logger.info(f"{settings.app_name} shutting down")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
register_error_handlers(app)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(tickets.router)
app.include_router(web.router)

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)