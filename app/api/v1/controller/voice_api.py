"""Voices API — curated ElevenLabs catalog for the UI voice picker."""

from fastapi import APIRouter, Query

from app.api.tags import Tags
from app.api.v1.response.base_response import BaseResponse, success_response
from app.service.voices_service import VoicesService

router = APIRouter(tags=[Tags.Voice])


@router.get("/voices", response_model=BaseResponse[list[dict]])
async def list_voices(
    gender: str | None = Query(default=None, description="Filter by gender (male/female)"),
    accent: str | None = Query(default=None, description="Filter by accent (British/American/...)"),
):
    """Return the curated voice catalog (id, name, gender, accent, blurb).

    Filters are optional; without them, returns the full catalog.
    """
    voices = VoicesService().list_voices(gender=gender, accent=accent)
    return success_response(voices, "Voices fetched")


@router.get("/voices/accents", response_model=BaseResponse[list[str]])
async def list_accents():
    """Distinct accent values in the catalog — drives the UI accent dropdown."""
    return success_response(VoicesService().list_accents(), "Accents fetched")
