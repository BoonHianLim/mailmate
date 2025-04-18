from typing import Annotated
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from fastapi import Depends

from src.services.email import get_email, send_email, mark_as_read as mark_as_read_service
from src.middleware.auth import require_auth
from src.utils.logging import LoggingRoute

router = APIRouter(
    prefix="/email",
    tags=["email"],
    route_class=LoggingRoute
)


@router.get("/")
async def get(count: int | None = 10,
              includeRead: bool | None = False,
              q: Annotated[list[str] | None, Query()] = None,
              token: str = Depends(require_auth)):
    return {"message": get_email(token, count, includeRead, q)}


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    threadId: str | None = None
    id: str | None = None


@router.post("/send")
async def send(request: SendEmailRequest, token: str = Depends(require_auth)):
    if not request.to:
        raise HTTPException(status_code=400, detail="to is required")
    if not request.subject:
        raise HTTPException(status_code=400, detail="subject is required")
    if not request.body:
        raise HTTPException(status_code=400, detail="body is required")
    if (request.threadId and not request.id) or (not request.threadId and request.id):
        raise HTTPException(
            status_code=400, detail="threadId and id are required together")

    return send_email(token, request.to, request.subject, request.body, request.id, request.threadId)


class MarkAsReadRequest(BaseModel):
    ids: list[str]


@router.post("/mark-as-read")
async def mark_as_read(request: MarkAsReadRequest, token: str = Depends(require_auth)):
    if not request.ids:
        raise HTTPException(status_code=400, detail="ids is required")
    success = mark_as_read_service(token, request.ids)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to mark emails as read")
    return {"message": "Emails marked as read successfully"}

