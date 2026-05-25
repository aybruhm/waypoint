from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from src.application.checkpoints_router import CheckpointAPIRouter
from src.application.executions_router import ExecutionAPIRouter
from src.domain.services.checkpoints_service import CheckpointService
from src.domain.services.events_service import EventService
from src.domain.services.replay_engine import ReplayEngine
from src.infrastructure.dbs.postgres.checkpoints.daos import CheckpointDAO
from src.infrastructure.dbs.postgres.engine import check_connection, cleanup_connections
from src.infrastructure.dbs.postgres.events.daos import EventDAO


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_connection()

    yield

    await cleanup_connections()


app = FastAPI(
    title="Waypoint",
    description="Agent Execution Recovery via Event Sourcing",
    lifespan=lifespan,
    root_path="/api",
)
v1_router = APIRouter(prefix="/v1")


@app.get("/")
async def check_root():
    return 1


@app.get("/health")
async def check_server_health():
    return 1


# Initialize DAOs
events_dao = EventDAO()
checkpoints_dao = CheckpointDAO()

# Initialize services
events_service = EventService(event_dao=events_dao)
checkpoints_service = CheckpointService(checkpoint_dao=checkpoints_dao)
replay_engine = ReplayEngine(
    events_service=events_service,
    checkpoints_service=checkpoints_service,
)

# Initialize routers
execution_router = ExecutionAPIRouter(
    replay_engine=replay_engine,
    events_service=events_service,
)
checkpoint_router = CheckpointAPIRouter(
    checkpoints_service=checkpoints_service,
    events_service=events_service,
)

# Register routers to base router
v1_router.include_router(
    execution_router.router,
    prefix="/executions",
    tags=["Executions"],
)
v1_router.include_router(
    checkpoint_router.router,
    prefix="/checkpoints",
    tags=["Checkpoints"],
)

# Mount vN router to app
app.include_router(router=v1_router)
