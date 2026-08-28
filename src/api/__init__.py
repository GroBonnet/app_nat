from fastapi import APIRouter

from src.api.routers.athletes import athlete_router
from src.api.routers.competitions import competition_router

router = APIRouter(prefix="/v1")

router.include_router(competition_router)
router.include_router(athlete_router)
