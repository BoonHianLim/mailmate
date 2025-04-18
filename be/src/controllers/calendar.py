from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.utils.logging import LoggingRoute
from src.services.calendar import get_events, add_event as add_event_service
from src.middleware.auth import require_auth

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
    route_class=LoggingRoute
)


@router.get("/")
def get(start: str | None = None, end: str | None = None, token: str = Depends(require_auth)):
    return get_events(token, start, end, "primary")


class AddEventReq(BaseModel):
    summary: str
    location: str | None = None
    description: str | None = None
    start: dict[str, str]
    end: dict[str, str]


@router.post("/event")
def add_event(request: AddEventReq, token: str = Depends(require_auth)):
    if not request.start.get("dateTime"):
        raise HTTPException(
            status_code=400, detail="start.dateTime is required")
    try:
        datetime.fromisoformat(request.start.get("dateTime"))
    except:
        raise HTTPException(
            status_code=400, detail="start.dateTime is not a valid datetime")

    if not request.end.get("dateTime"):
        raise HTTPException(status_code=400, detail="end.dateTime is required")
    try:
        datetime.fromisoformat(request.end.get("dateTime"))
    except:
        raise HTTPException(
            status_code=400, detail="end.dateTime is not a valid datetime")

    if not request.summary:
        raise HTTPException(status_code=400, detail="summary is required")
    return add_event_service(token, request.summary, request.location, request.description, request.start, request.end)
