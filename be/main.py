from dotenv import load_dotenv
from fastapi import FastAPI
import logging
import os
from contextlib import asynccontextmanager
import sys

from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.repo.auth import load_user_tokens
from src.utils.logging import setup_logger
from src.controllers import email
from src.controllers import auth
from src.controllers import calendar
from src.controllers import assistant
from src.utils.logging import LoggingRoute

load_dotenv()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
setup_logger()
logger: logging.Logger = logging.getLogger('uvicorn.error')
print = logger.info


def receive_signal(signalNumber, frame):
    print('Received:', signalNumber)
    sys.exit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    import signal
    signal.signal(signal.SIGINT, receive_signal)
    load_user_tokens()
    logger.info("Pre-startup preparation completed. Starting FastAPI server...")
    # startup tasks
    yield
    # Clean up the ML models and release the resources

app = FastAPI(lifespan=lifespan)
app.router.route_class = LoggingRoute

app.add_middleware(SessionMiddleware, secret_key="your_secret_key")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


app.include_router(auth.router)
app.include_router(email.router)
app.include_router(calendar.router)
app.include_router(assistant.router)
