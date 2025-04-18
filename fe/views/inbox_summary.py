import streamlit as st
import requests
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
from urllib.parse import unquote

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

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-001",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=GOOGLE_API_KEY,
)

st.set_page_config(page_title="Inbox Summary", page_icon="📨")
st.title("📨 Inbox Summary")


# Function to retrieve cookies from Streamlit context
def get_all_cookies():
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


# Function to fetch emails via API using cookies
def fetch_emails():
    try:
        cookies = get_all_cookies()
        cookies_request = {"key": cookies.get("key", "")}
        response = requests.get(
            f"http://{ip_address}:8101/email", cookies=cookies_request
        )
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
                "sender": sender,
                "summary": raw,
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


# Function to mark emails as read using their IDs
def mark_emails_as_read():
    unread_ids = st.session_state.get("unread_email", [])
    if not unread_ids:
        st.warning("No unread emails to mark as read.")
        return

    payload = {"ids": unread_ids}
    cookies = get_all_cookies()
    cookies_request = {"key": cookies.get("key", "")}

    try:
        response = requests.post(
            f"http://{ip_address}:8101/email/mark-as-read",
            json=payload,
            cookies=cookies_request,
        )
        response.raise_for_status()
        st.success("✅ Unread emails marked as read.")
        # Optionally clear unread state
        st.session_state["unread_email"] = []
    except Exception as e:
        st.error(f"❌ Failed to mark emails as read: {e}")


# Summarize emails using LLM
def summarize_emails(emails):
    email_contents = ""
    for email in emails:
        email_contents += f"From: {email['sender']}\nSubject: {email['subject']}\nSummary: {email['summary']}\n\n"

    prompt = f"""
        You are a thoughtful assistant analyzing a user's inbox. Below are the contents of recent emails:

        {email_contents}

        Please follow this step-by-step reasoning process:

        1. Carefully read through each email.
        2. Identify the sender, subject, and key content of each message.
        3. Determine the purpose or intent of each email (e.g., update, request, reminder, event).
        4. Spot any high-priority items, urgent tasks, or time-sensitive actions.
        5. Group related emails (e.g., same sender, similar topic).
        6. Reflect on the overall themes or trends across the inbox.
        7. Based on this reasoning, provide a structured summary that includes:
        - Key updates and themes
        - Actionable items with deadlines (if any)
        - High-priority messages
        - Upcoming meetings or events

        Present your output in a clear, concise format (e.g., bullet points or short sections) suitable for a busy user skimming for insight.
    """

    try:
        prompt_template = ChatPromptTemplate.from_template(prompt)
        chain = prompt_template | llm
        response = chain.invoke({})
        return response.content
    except Exception as e:
        return f"Error generating summary: {e}"


# Session state
if "emails" not in st.session_state:
    st.session_state["emails"] = fetch_emails()
    st.session_state["last_fetch_time"] = datetime.now()

st.markdown("---")
st.subheader("📜 AI-Generated Inbox Summary")

if st.button("📄 Generate Summary with LLM"):
    with st.spinner("Summarizing emails..."):
        summary = summarize_emails(st.session_state["emails"])
    with st.expander("📖 View Full Summary", expanded=True):
        st.markdown(summary)

if st.button("✅ Mark All as Read"):
    with st.spinner("Marking emails as read..."):
        mark_emails_as_read()
