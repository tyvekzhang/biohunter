# SPDX-License-Identifier: MIT
"""
Server startup that include register router、session、cors、global exception
handler、jwt, openapi...
"""

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastlib import ConfigManager, exception, openapi, router
from fastlib.constants import RESOURCE_DIR
from fastlib.db_engine import get_async_engine
from fastlib.logging import logger
from fastlib.middleware.db_session import (
    SQLAlchemyMiddleware,
)
from fastlib.middleware.jwt import jwt_middleware
from starlette.middleware.cors import CORSMiddleware

# Load config
server_config = ConfigManager.get_server_config()
security_config = ConfigManager.get_security_config()


# Setup fastapi instance
app = FastAPI(
    docs_url=None,
    redoc_url=None,
    title=server_config.name,
    version=server_config.version,
    description=server_config.app_desc,
)

# Register middleware
app.add_middleware(SQLAlchemyMiddleware, custom_engine=get_async_engine())
origins = [origin.strip() for origin in security_config.backend_cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(jwt_middleware)

# Register exception handler
exception.register_exception_handlers(app)

# Setup router
current_dir = Path(__file__).parent.absolute()
controller_path = os.path.join(current_dir, "controller")
if server_config.enable_api_prefix:
    app.include_router(
        router.register_router([controller_path]),
        prefix=server_config.api_prefix,
    )
else:
    app.include_router(
        router.register_router([controller_path]),
    )
# Register offline openapi
openapi.register_offline_openapi(app=app, resource_dir=RESOURCE_DIR)


def run():
    logger.info(f"OpenAPI url: http://{server_config.host}:{server_config.port}/docs")
    uvicorn.run(
        app="src.main.app.server:app",
        host=server_config.host,
        port=server_config.port,
        workers=server_config.workers,
    )
