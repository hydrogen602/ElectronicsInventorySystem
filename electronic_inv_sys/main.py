from contextlib import asynccontextmanager
import os
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from fastapi.staticfiles import StaticFiles

from electronic_inv_sys.infrastructure.digikey_api import AuthException
from electronic_inv_sys.infrastructure.env_config import EnvConfig
from electronic_inv_sys.services import (
    ServicesProviderSingleton,
    services_factory as services_factory,
)
from electronic_inv_sys.web_api import router as web_api_router

ENV_CONFIG = EnvConfig()


@asynccontextmanager
async def service_lifespan(app: FastAPI):
    async with services_factory(ENV_CONFIG) as s:
        s.config.log_set_vars()
        ServicesProviderSingleton(s)
        yield
        ServicesProviderSingleton.delete_instance()


# Configure root_path for nginx proxy
root_path = os.environ.get("ROOT_PATH", "")
app = FastAPI(lifespan=service_lifespan, root_path=root_path)

# Set up CORS
origins: list[str] = []
if url := ENV_CONFIG.get("ALLOWED_FRONTEND_URLS"):
    logger.info("Adding url(s) to allowed origins: {}", url)
    origins.extend(url.split())

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def remove_fastapi_traceback[T: Exception](exc: T) -> T:
    try:
        # FastAPI has 4 frames in the traceback - try to trim those off
        return exc.with_traceback(
            exc.__traceback__.tb_next.tb_next.tb_next.tb_next  # pyright: ignore[reportOptionalMemberAccess]
        )
    except AttributeError:
        return exc


@app.exception_handler(AuthException)
def auth_exception_handler(  # pyright: ignore[reportUnusedFunction]
    request: Request, exc: AuthException
) -> Any:
    exc = remove_fastapi_traceback(exc)

    logger.opt(exception=exc).error("Auth error: {}", str(exc))

    return PlainTextResponse(content=f"Authentication error: {exc}", status_code=401)


@app.exception_handler(KeyError)
def key_error_handler(request: Request, exc: KeyError) -> Any:
    exc = remove_fastapi_traceback(exc)

    logger.opt(exception=exc).error("Key error: {}", str(exc))
    return PlainTextResponse(content=str(exc), status_code=404)


@app.exception_handler(ValidationError)
def validation_error_handler(request: Request, exc: ValidationError) -> Any:
    exc = remove_fastapi_traceback(exc)

    errs = exc.errors(include_url=False)
    logger.opt(exception=exc).error(
        "Validation error: {}: original: {}", str(exc), errs
    )
    return PlainTextResponse(content=str(exc), status_code=500)


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError) -> Any:
    exc = remove_fastapi_traceback(exc)

    logger.opt(exception=exc).error("Value error: {}", str(exc))
    return PlainTextResponse(content=str(exc), status_code=400)


app.include_router(web_api_router, prefix="/api")

if os.environ.get("RUNNING_IN_DOCKER"):
    logger.info("Running in docker - so serving static files directly")

    # when someone requests index.html, favicon.ico, robots.txt or asset-manifest.json, serve it directly
    @app.get("/")
    def direct_file_index():
        return FileResponse("index.html")

    @app.get("/favicon.ico")
    def direct_file_favicon():
        return FileResponse("favicon.ico")

    @app.get("/robots.txt")
    def direct_file_robots():
        return FileResponse("robots.txt")

    @app.get("/asset-manifest.json")
    def direct_file_asset_manifest():
        return FileResponse("asset-manifest.json")

    app.mount("/static", StaticFiles(directory="static"), name="static")

else:
    logger.info("Not running in docker - skipping static file serving")

    @app.get("/")
    def index():
        return {"message": "Hello, World!"}
