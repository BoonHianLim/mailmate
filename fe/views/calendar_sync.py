from dotenv import load_dotenv
import streamlit as st
import streamlit.components.v1 as components
import json
import os
import re
import ast
from datetime import datetime, timedelta, timezone
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from urllib.parse import unquote

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

ip_address = os.getenv("IP_ADDRESS", "localhost")  # default fallback to localhost

# Fallback to session_state if not found in .env
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = st.session_state.get("google_api_key")

# Warn user if no API key is available
if not GOOGLE_API_KEY:
    st.error(
        "❌ Google API Key is missing. Please log in and set your API key in the sidebar."
    )
    st.stop()

# Initialize session state for tracking added events
if "added_events" not in st.session_state:
    st.session_state.added_events = set()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-001",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=GOOGLE_API_KEY,
)

st.set_page_config(page_title="Calendar Sync", page_icon="📅")
st.title("📅 Calendar Sync")

info_container = st.empty()
info_container.info("📌 Analyzing emails from API using LLM to detect calendar events.")

# Endpoints
CALENDAR_API_URL = (
    f"http://{ip_address}:8101/calendar/event"  # Used for both GET and POST
)
EMAIL_API_URL = f"http://{ip_address}:8101/email"  # Endpoint to fetch emails
events_URL = f"http://{ip_address}:8101/calendar"  # GET endpoint to fetch existing Google Calendar events

# Load or update embed_url
calendar_json_path = "calendar.json"


def load_embed_url():
    if os.path.exists(calendar_json_path):
        with open(calendar_json_path, "r") as f:
            data = json.load(f)
            return data.get("embed_url")
    return None


def save_embed_url(new_url):
    with open(calendar_json_path, "w") as f:
        json.dump({"embed_url": new_url}, f)


# Sidebar input logic
change_calendar = st.sidebar.button("🔄 Change Calendar")
embed_url = load_embed_url()

if not embed_url or change_calendar:
    st.sidebar.markdown("Please enter a public Google Calendar embed URL:")
    new_url = st.sidebar.text_input(
        "Calendar Embed URL", value=embed_url or "", key="calendar_input"
    )
    if new_url and new_url.startswith("https://calendar.google.com/calendar/embed?"):
        save_embed_url(new_url)
        embed_url = new_url
        st.sidebar.success("✅ Calendar URL saved!")
        st.rerun()
    elif new_url:
        st.sidebar.warning(
            "⚠️ Invalid calendar embed URL. Make sure it starts with 'https://calendar.google.com/calendar/embed?'"
        )

# If still no embed_url after input step, block iframe and notify user
if not embed_url:
    st.warning(
        "⚠️ No calendar URL provided yet. Please enter it in the sidebar to see your calendar."
    )
else:
    st.markdown("---")
    st.markdown("### My Google Calendar")
    components.html(
        f'<iframe src="{embed_url}" style="border: 0" width="700" height="600" frameborder="0" scrolling="no"></iframe>',
        height=600,
    )


def get_all_cookies():
    """Return cookies as a dictionary using st.context.headers."""
    headers = st.context.headers
    if headers is None or "cookie" not in headers:
        return {}
    cookie_string = headers["cookie"]
    cookie_kv_pairs = cookie_string.split(";")
    cookie_dict = {}
    for kv in cookie_kv_pairs:
        if "=" in kv:
            key, value = kv.split("=", 1)
            cookie_dict[key.strip()] = unquote(value.strip())
    return cookie_dict


def fetch_emails():
    """Fetch emails from the API endpoint."""
    try:
        cookies = get_all_cookies()
        cookies_request = {"key": cookies.get("key", "")}
        response = requests.get(EMAIL_API_URL, cookies=cookies_request)
        response.raise_for_status()
        data = response.json()
        emails_data = data.get("message", [])
    except Exception as e:
        st.error(f"Failed to fetch emails from API: {e}")
        return []

    processed_emails = []
    unread_ids = []  # <- Store email IDs here
    for email in emails_data:
        sender = email.get("from", "Unknown Sender")
        subject = email.get("subject", "No Subject")
        raw = email.get("raw", "")
        thread_id = email.get("threadId", "")
        date_str = email.get("date", None)
        try:
            date_obj = (
                datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
                if date_str
                else datetime.now()
            )
        except Exception:
            date_obj = datetime.now()
        email_id = email.get("id", str(date_obj.timestamp()))
        processed_emails.append(
            {
                "id": email_id,
                "subject": subject,
                "from": sender,
                "raw": raw,
                "threadId": thread_id,
                "priority": (
                    "High" if "IMPORTANT" in email.get("labelIds", []) else "Low"
                ),
                "date": date_obj,
            }
        )
        unread_ids.append(email_id)  # <- Add ID to the list

    # Save to session state
    st.session_state["unread_email"] = unread_ids
    return processed_emails


def get_existing_events():
    """
    Fetch existing Google Calendar events from the calendar API using cookies.
    The endpoint returns events in JSON format with ISO datetime strings.
    """
    cookies = get_all_cookies()
    cookies_request = {"key": cookies.get("key", "")}
    try:
        response = requests.get(events_URL, cookies=cookies_request)

        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching existing events: {e}")
        return []


def extract_event_from_email_llm(email):
    """
    Use the LLM to extract calendar event details from an email.

    The prompt instructs the LLM to return a JSON object with:
    - "title": the event title,
    - "date_time": the event date and time in "YYYY-MM-DD HH:MM" format,
    - "description": a brief description of the event.

    If no event is detected, output an empty JSON object: {}.
    """
    subject = email.get("subject", "")
    body = email.get("raw", "")
    today_str = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
You are an assistant that extracts calendar event details from emails.
Today is {today_str}. Use this information to correctly infer the event year when only the month and day are provided.
Examine the email below and if a calendar event is present, output a JSON object with the following keys:
- "title": the event title,
- "date_time": the event date and time in "YYYY-MM-DD HH:MM" format,
- "description": a brief description of the event. If no explicit description is provided, infer or guess a short summary or provide a placeholder.

If the email does not contain a calendar event, output an empty JSON object: {{}}

Email Subject: {subject}
Email Body: {body}

Example output:
{{
  "title": "Project Sync Meeting",
  "date_time": "2025-04-06 14:00",
  "description": "Discussion about project updates and timelines (guessed or inferred)."
}}

Only output the JSON object.
"""
    try:
        response = llm.invoke(prompt)

        output = response.content.strip()
        output = re.sub(r"```(?:json|python)?", "", output).strip("` \n")
        try:
            event_data = json.loads(output)
        except Exception:
            event_data = ast.literal_eval(output)
        if isinstance(event_data, dict):
            return event_data
        else:
            return {}
    except Exception as e:
        st.error(f"LLM extraction error: {e}")
        return {}


# Process emails from the API
emails = fetch_emails()
detected_events = []
for email in emails:
    event = extract_event_from_email_llm(email)
    if event and "title" in event and event.get("date_time"):
        event["source"] = f"Email from {email.get('from', 'unknown')}"
        try:
            # Parse the LLM date string and immediately attach Asia/Singapore timezone.
            dt = datetime.strptime(event["date_time"], "%Y-%m-%d %H:%M")
            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
        except Exception:
            dt = datetime.now(timezone(timedelta(hours=8)))
        event["date_time"] = dt
        thread_id = email.get("threadId", "")
        email_id = email.get("id", "")
        event["unique_id"] = f"{thread_id}_{email_id}_{dt.isoformat()}"
        # Only add events that haven't been added before
        if event["unique_id"] not in st.session_state.added_events:
            detected_events.append(event)

info_container.empty()

# Fetch existing calendar events immediately for collision detection.
existing_events = get_existing_events()

if not detected_events:
    st.info("No new events detected from emails.")
else:
    st.markdown("### Detected Events")
    events_to_remove = []  # Track events that get added during this session

    for event in detected_events:
        # The LLM date is now timezone-aware in Asia/Singapore.
        start_time = event["date_time"]
        end_time = start_time + timedelta(hours=1)

        collision_found = False
        collision_message = ""
        for existing in existing_events:
            try:
                existing_start = datetime.fromisoformat(existing["start"]["dateTime"])
                existing_end = datetime.fromisoformat(existing["end"]["dateTime"])
            except Exception:
                continue
            # Check if the new event overlaps with an existing event.
            if start_time < existing_end and end_time > existing_start:
                collision_found = True
                collision_message = (
                    f"Collision with '{existing.get('summary', 'Unnamed event')}' "
                    f"from {existing_start.strftime('%Y-%m-%d %H:%M')} to {existing_end.strftime('%Y-%m-%d %H:%M')}."
                )
                break

        with st.container():
            st.markdown(
                f"""
                <div style='border: 1px solid #ddd; padding: 15px; margin-bottom: 15px;
                            border-radius: 8px; background-color: #f9f9f9;'>
                    <h4 style='margin-bottom: 10px;'>{event.get("title", "")}</h4>
                    <p style='margin: 5px 0;'><strong>Date & Time:</strong> {start_time.strftime("%A, %B %d, %Y %I:%M %p")}</p>
                    <p style='margin: 5px 0;'><strong>Description:</strong> {event.get("description", "")}</p>
                    <p style='margin: 5px 0; color: {"red" if collision_found else "green"};'>
                        {"Collision detected: " + collision_message if collision_found else "No conflict detected."}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Only show the "Add to Google Calendar" button if no collision is detected.
            if not collision_found:
                if st.button("Add to Google Calendar", key=event.get("unique_id")):
                    # Re-check collision before adding.
                    collision_found = False
                    for existing in existing_events:
                        try:
                            existing_start = datetime.fromisoformat(
                                existing["start"]["dateTime"]
                            )
                            existing_end = datetime.fromisoformat(
                                existing["end"]["dateTime"]
                            )
                        except Exception:
                            continue
                        if start_time < existing_end and end_time > existing_start:
                            collision_found = True
                            collision_message = (
                                f"There is a collision with '{existing.get('summary', 'Unnamed event')}' "
                                f"from {existing_start.strftime('%Y-%m-%d %H:%M')} to {existing_end.strftime('%Y-%m-%d %H:%M')}."
                            )
                            break

                    if collision_found:
                        st.error(collision_message)
                    else:
                        payload = {
                            "summary": event.get("title", ""),
                            "start": {"dateTime": start_time.isoformat()},
                            "end": {"dateTime": end_time.isoformat()},
                            "description": event.get("description", ""),
                        }
                        cookies = get_all_cookies()
                        cookies_request = {"key": cookies.get("key", "")}
                        try:
                            response = requests.post(
                                CALENDAR_API_URL, json=payload, cookies=cookies_request
                            )
                            response.raise_for_status()
                            st.success(
                                f"Event '{event.get('title', '')}' added to Google Calendar!"
                            )

                            # Add this event to the set of added events
                            st.session_state.added_events.add(event["unique_id"])
                            events_to_remove.append(event["unique_id"])

                            # Optionally, update existing_events to include the new event.
                            new_event = {
                                "start": {"dateTime": start_time.isoformat()},
                                "end": {"dateTime": end_time.isoformat()},
                                "summary": event.get("title", ""),
                            }
                            existing_events.append(new_event)
                        except Exception as e:
                            st.error(f"Error adding event: {e}")

    # Trigger a rerun to refresh the UI and remove added events
    if events_to_remove:
        st.rerun()

st.markdown("---")
st.markdown("### My Google Calendar")
if embed_url:
    components.html(
        f'<iframe src="{embed_url}" style="border: 0" width="700" height="600" frameborder="0" scrolling="no"></iframe>',
        height=600,
    )
