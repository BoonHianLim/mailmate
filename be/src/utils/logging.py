import logging
import logging.config
import os
import time
import sys

from fastapi import Response, Request
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
from fastapi.routing import APIRoute
from typing import Callable

logger: logging.Logger = logging.getLogger('uvicorn.error')

_current_datetime = time.strftime("%Y%m%d")
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_grandparent_dir = os.path.dirname(_parent_dir)
log_path = os.path.join(_grandparent_dir, "logs")
log_file_path = os.path.join(log_path, _current_datetime + '.log')

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "level": "NOTSET",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": log_file_path,
            "mode": "a",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "": {  # root logger
            "level": "NOTSET",
            "handlers": ["default", "file"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "NOTSET",
            "handlers": ["default", "file"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "NOTSET",
            "handlers": ["default", "file"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "NOTSET",
            "handlers": ["default", "file"],
            "propagate": False,
        },
    },
}


def setup_logger():
    sys.stderr.reconfigure(encoding="utf-8")
    os.makedirs(log_path, exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("Logging initialized")


class LoggingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            logger = logging.getLogger("uvicorn.error")
            req_body = await request.body()
            logger.info(f"{req_body} {request.url.path} {request.method}")

            response = await original_route_handler(request)
            if isinstance(response, StreamingResponse):
                logger.debug(
                    "StreamingResponse: Body not available for logging")
            elif response.background:
                response.background.add_task(
                    BackgroundTask(logger.debug, response.body))
            else:
                response.background = BackgroundTask(
                    logger.debug, response.body)
            return response

        return custom_route_handler
