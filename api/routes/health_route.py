from fastapi import APIRouter
from models.schemas import PingResponse

health_router = APIRouter()

@health_router.get("/ping", response_model=PingResponse)
async def keep_alive_ping():
    return PingResponse(status="awake")