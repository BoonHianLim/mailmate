import asyncio
from io import StringIO
import logging
import time
from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse
from pydantic import BaseModel

from tools.tools import call_tool
from src.utils.logging import LoggingRoute
from src.middleware.auth import require_auth

logger: logging.Logger = logging.getLogger('uvicorn.error')


router = APIRouter(
    prefix="/assistant",
    tags=["assistant"],
    route_class=LoggingRoute
)


async def generate_data():
    for i in range(10):
        yield f"Line {i}\n"
        await asyncio.sleep(1)


class ChatRequest(BaseModel):
    messages: str
    system: str | None = None


@router.post("/chat")
async def chat(request: ChatRequest, token: str = Depends(require_auth)):
    response = call_tool(token, request.messages, request.system)
    logger.info(f"Response: {response}")
    return StreamingResponse(
        StringIO(response),
        media_type="text/plain",
    )
