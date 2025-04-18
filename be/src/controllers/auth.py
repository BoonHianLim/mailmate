import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel
from uuid import uuid4

from src.repo.auth import save_user_tokens, set_user_tokens
from src.utils.logging import LoggingRoute

logger: logging.Logger = logging.getLogger('uvicorn.error')

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    route_class=LoggingRoute
)

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.send",
          "https://www.googleapis.com/auth/gmail.modify",
          "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
          "https://www.googleapis.com/auth/calendar.events"]


@router.get("/login")
def login(request: Request):
    """ Initiates the OAuth flow """
    logger.info("Starting OAuth flow")
    CURRENT_HOSTNAME = os.getenv("CURRENT_HOSTNAME", "http://127.0.0.1:8101")
    # This is a backend endpoint
    REDIRECT_URI = f"{CURRENT_HOSTNAME}/auth/callback"
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt="consent"
    )
    request.session["state"] = state  # temp solution to store state in memory
    return RedirectResponse(authorization_url)


@router.get("/callback")
async def callback(request: Request):
    STREAMLIST_HOSTNAME = os.getenv(
        "STREAMLIST_HOSTNAME", "http://127.0.0.1:8501")
    CURRENT_HOSTNAME = os.getenv("CURRENT_HOSTNAME", "http://localhost:8101")
    # This is a backend endpoint
    REDIRECT_URI = f"{CURRENT_HOSTNAME}/auth/callback"
    state = request.session.get("state")
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state
    )

    # Use the full URL (which contains the code and state) for fetching the token
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials

    new_uuid = uuid4()
    logger.info(f"New uuid: {new_uuid}")
    set_user_tokens(str(new_uuid), {
        "credentials": {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,

        },
    })
 # Store the credentials in the session.
    save_user_tokens()  # Save the tokens to a file or database
    # At this point, you have the tokens. You might store them, set a session cookie, etc.
    # Then redirect the user back to your frontend application.
    response = RedirectResponse(STREAMLIST_HOSTNAME)  # Redirect to frontend
    response.set_cookie(
        key="key",
        value=new_uuid,
        httponly=True,     # Prevent JS access
        secure=False,       # Send only over HTTPS
        samesite="lax",    # Or 'strict'/'none' depending on FE/BE domains
        max_age=60 * 60 * 24,  # 1 day
        path="/"
    )
    return response
