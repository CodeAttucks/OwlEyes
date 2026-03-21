import os
from typing import Any

import httpx
from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix="/base44", tags=["base44"])

ALLOWED_PROJECT_FIELDS = {
    "name",
    "description",
    "status",
    "priority",
    "budget",
    "spent",
    "start_date",
    "end_date",
    "completion_percentage",
    "project_manager",
    "region",
    "fiber_miles_planned",
    "fiber_miles_completed",
    "locations_served",
    "latitude",
    "longitude",
}


def _base44_config() -> tuple[str, str]:
    app_id = os.getenv("BASE44_APP_ID", "").strip()
    api_key = os.getenv("BASE44_API_KEY", "").strip()
    base_url = os.getenv("BASE44_API_BASE_URL", "").strip().rstrip("/")

    if not app_id:
        raise HTTPException(status_code=500, detail="Missing BASE44_APP_ID")
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing BASE44_API_KEY")
    if not base_url:
        raise HTTPException(status_code=500, detail="Missing BASE44_API_BASE_URL")

    return f"{base_url}/api/apps/{app_id}/entities/Project", api_key


async def _request_base44(method: str, url: str, api_key: str, payload: dict[str, Any] | None = None) -> Any:
    headers = {
        "api_key": api_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.request(method, url, headers=headers, json=payload)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Base44 upstream request failed: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Base44 upstream returned invalid JSON") from exc


@router.get("/projects")
async def fetch_project_entities():
    endpoint, api_key = _base44_config()
    return await _request_base44("GET", endpoint, api_key)


@router.put("/projects/{entity_id}")
async def update_project_entity(entity_id: str, update_data: dict[str, Any] = Body(...)):
    endpoint, api_key = _base44_config()

    filtered_update = {
        key: value for key, value in update_data.items() if key in ALLOWED_PROJECT_FIELDS
    }
    if not filtered_update:
        raise HTTPException(status_code=400, detail="No valid Project fields provided for update")

    return await _request_base44("PUT", f"{endpoint}/{entity_id}", api_key, filtered_update)
