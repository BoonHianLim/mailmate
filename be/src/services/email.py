import traceback
from bs4 import BeautifulSoup
import logging
from email.message import EmailMessage
import base64
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from src.repo.auth import get_user_tokens
logger: logging.Logger = logging.getLogger('uvicorn.error')


def get_gmail_service(token: str):
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
    return build("gmail", "v1", credentials=creds)


def extract_text_from_html(html: str) -> str:
    """
    Extracts and returns all text content from the given HTML string.

    :param html: A string containing HTML.
    :return: A string of extracted text content.
    """
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text(separator=' ', strip=True)


def get_email(token: str, count: int = 10, include_read: bool = False, keywords: list[str] | None = None):
    """ Fetches the specified number of emails in the user's inbox """
    logger.info(
        f"Fetching emails with count: {count}, include_read: {include_read}, keywords: {keywords}")
    service = get_gmail_service(token)
    try:
        # Build the query string
        query_parts = ["in:inbox"]
        if not include_read:
            query_parts.append("is:unread")
        if keywords:
            quoted_keywords = [f'"{kw}"' for kw in keywords]
            query_parts.append(" OR ".join(quoted_keywords))

        query_string = " ".join(query_parts)

        logger.info(f"Query string: {query_string}")
        results = service.users().messages().list(
            userId="me",
            maxResults=count,
            q=query_string
        ).execute()

        messages = results.get("messages", [])

        if not messages:
            return []

        emails = []
        for message in messages:
            msg_id = message["id"]
            msg_data = service.users().messages().get(userId="me", id=msg_id,
                                                      format="full").execute()

            # Extract email details
            content = None

            payload = msg_data.get("payload", {})
            headers = payload.get("headers", [])
            parts = payload.get("parts", [])
            for part in parts:
                body = part.get("body", None)
                if not body:
                    continue
                encryted_data = body.get("data", None)
                if not encryted_data:
                    continue
                html_content = base64.urlsafe_b64decode(encryted_data).decode()
                content = extract_text_from_html(html_content)
                break

            email_subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            email_from = next(
                (h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
            email_snippet = msg_data.get("snippet", None)

            unix_milli = msg_data.get("internalDate", None)
            # Convert to seconds
            timestamp_s = int(unix_milli) / 1000
            dt_utc = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
            date_str = dt_utc.isoformat()

            if not content:
                content = email_snippet
            
            if not email_snippet:
                email_snippet = content[:50] + "..." if len(content) > 50 else content

            emails.append({
                "from": email_from,
                "subject": email_subject,
                "snippet": email_snippet,
                "raw": content,
                "threadId": msg_data.get("threadId", None),
                "id": msg_id,
                "labelIds": msg_data.get("labelIds", []),
                "date": date_str,
            })

        return emails

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


def create_message(sender, to, subject, message_text, id: str | None = None, thread_id: str | None = None):
    message = EmailMessage()
    message.set_content(message_text)
    message['To'] = to
    message['From'] = sender
    message['Subject'] = subject
    if id:
        message['In-Reply-To'] = id
        message['References'] = id

    end_message = {
        "raw": base64.urlsafe_b64encode(message.as_bytes()).decode(),
    }
    if thread_id:
        end_message["threadId"] = thread_id
    return end_message


def send_email(token: str, to: str, subject: str, message_text: str, id: str | None = None, thread_id: str | None = None):
    service = get_gmail_service(token)
    profile = service.users().getProfile(userId='me').execute()
    email_address = profile['emailAddress']
    try:
        message = create_message(
            email_address, to, subject, message_text, id, thread_id)
        response = service.users().messages().send(userId="me", body=message).execute()
        return {'id': response['id'], 'threadId': response['threadId']}
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.error(f"{traceback.format_exc()}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


def mark_as_read(token: str, ids: list[str]) -> bool:
    service = get_gmail_service(token)
    try:
        for id in ids:
            service.users().messages().modify(
                userId='me', id=id, body={'removeLabelIds': ['UNREAD']}).execute()
            logger.debug(f'Marked message {id} as read.')
        return True
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.error(f"{traceback.format_exc()}")
        return False
