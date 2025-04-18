from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from src.repo.auth import get_user_tokens


def get_calendar_service(token: str):
    """ Returns an authenticated Gmail API service instance """
    creds = get_user_tokens(token)
    if creds is None:
        raise HTTPException(
            status_code=401, detail="User token not found.")
    user_cred = creds["credentials"]
    if not user_cred:
        raise HTTPException(
            status_code=401, detail="User credentials not found.")
    creds = Credentials(
        token=user_cred["access_token"],
        refresh_token=user_cred["refresh_token"],
        token_uri=user_cred["token_uri"],
        client_id=user_cred["client_id"],
        client_secret=user_cred["client_secret"],
    )
    return build("calendar", "v3", credentials=creds)


def get_events(token: str, start: Optional[str], end: Optional[str], calendar_id) -> list:
    """ Fetches events from the user's calendar """
    if start is None:
        start = datetime.now(tz=timezone.utc).isoformat()

    service = get_calendar_service(token)

    try:
        events_result: dict = None
        if end is None:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
        else:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start,
                timeMax=end,
                maxResults=100,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
        events = events_result.get("items", [])
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def add_event(token: str, summary: str, location: str | None, description: str | None, start: dict[str, str], end: dict[str, str]) -> dict:
    """ Adds an event to the user's calendar """
    service = get_calendar_service(token)

    event = {
        "summary": summary,
        "location": location or "",
        "description": description or "",
        "start": {
            "dateTime": start.get("dateTime"),
            "timeZone": start.get("timeZone", "Asia/Singapore"),
        },
        "end": {
            "dateTime": end.get("dateTime"),
            "timeZone": end.get("timeZone", "Asia/Singapore"),
        },
    }

    try:
        event_result = service.events().insert(calendarId="primary", body=event).execute()
        return event_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))