from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from src.infrastructure.dbs.postgres.engine import check_connection, cleanup_connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_connection()

    yield

    await cleanup_connections()


app = FastAPI(lifespan=lifespan)
base_router = APIRouter(prefix="/v1")


@app.get("/health")
async def check_server_health():
    return 1
