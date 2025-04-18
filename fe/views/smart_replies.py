import requests
import streamlit as st
import json
import re
from langchain_community.chat_models import ChatOllama
from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from email.utils import parseaddr

# Load environment variables
dotenv_path = os.getenv("DOTENV_PATH", None)
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
ip_address = os.getenv("IP_ADDRESS", "localhost")  # default fallback
EMAIL_API_URL = f"http://{ip_address}:8101/email"  # Endpoint to fetch emails

# Fallback to session_state for API key
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = st.session_state.get("google_api_key")
if not GOOGLE_API_KEY:
    st.error(
        "❌ Google API Key is missing. Please log in and set your API key in the sidebar."
    )
    st.stop()

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-001",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=GOOGLE_API_KEY,
)

# Page config
st.set_page_config(page_title="Smart Replies", page_icon="✉️")
st.title("✉️ Smart Replies")

# Session state
if "generated_variations" not in st.session_state:
    st.session_state.generated_variations = None
if "generated_compose_variations" not in st.session_state:
    st.session_state.generated_compose_variations = None


def get_all_cookies():
    from urllib.parse import unquote

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
    try:
        cookies = get_all_cookies()
        response = requests.get(EMAIL_API_URL, cookies=cookies)
        response.raise_for_status()
        data = response.json()
        emails_data = data.get("message", [])
    except Exception as e:
        st.error(f"Failed to fetch emails from API: {e}")
        return []

    processed = []
    unread_ids = []
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
        # fallback to To header
        if "payload" in email:
            headers = email["payload"].get("headers", [])
            to_hdr = next((h["value"] for h in headers if h["name"] == "To"), "")
        else:
            to_hdr = email.get("to", "")
        display_name, _ = parseaddr(to_hdr)
        to_name = display_name or to_hdr or "Jerome"
        processed.append(
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
                "to_name": to_name,
            }
        )
        unread_ids.append(email_id)
    st.session_state["unread_email"] = unread_ids
    return processed


# Inbox display
st.subheader("Inbox Emails")
emails = fetch_emails()
if not emails:
    st.info("No emails available.")
else:
    for i, em in enumerate(emails):
        with st.expander(f"{em['subject']} - {em['from']}"):
            st.markdown(f"**Subject:** {em['subject']}")
            st.markdown(f"**Sender:** {em['from']}")
            st.markdown(f"**Date:** {em['date']}")
            st.markdown(f"**Content:** {em['raw']}")
            if st.button("Reply to this email", key=f"select_{i}"):
                st.session_state.selected_email = em
                st.session_state.generated_variations = None

# Reply interface
if "selected_email" in st.session_state:
    em = st.session_state.selected_email
    sender_name = em.get("from", "Unknown Sender")

    st.markdown("---")
    st.subheader("Compose Reply")
    additional_instructions = st.text_input(
        "Let the LLM know what you want to reply:", placeholder="e.g. I'll be there"
    )
    tone = st.radio("Choose reply tone:", ["Professional", "Friendly", "Concise"])
    multi = st.checkbox("Generate multiple variations to choose from")
    sign_off = st.text_input(
        "Your sign-off name:", placeholder="e.g. Jerome", key="reply_signoff"
    )
    if not sign_off:
        sign_off = "Jerome"
    if st.button("Generate Reply"):
        prompt = None
        content = em.get("raw", "")
        if multi:
            prompt = f"""
You are an assistant that generates smart email replies.

IMPORTANT: Only output the final reply text.

Email:
"{content}"
Instructions: "{additional_instructions}"
Generate 3 {tone.lower()} variations labeled:
===Variation 1===
===Variation 2===
===Variation 3===
Each must:
1. Start with "Dear {sender_name},"
2. End with "Best regards," then on the next line "{sign_off}"
3. Address the content
"""
        else:
            prompt = f"""
You are an assistant that generates smart email replies.

IMPORTANT: Only output the final reply text.

Email:
"{content}"
Instructions: "{additional_instructions}"
Generate a {tone.lower()} reply:
1. Start with "Dear {sender_name},"
2. End with "Best regards," then on the next line "{sign_off}"
3. Address the content
"""
        response = llm.invoke(prompt)
        out = response.content.strip()
        lines = out.splitlines()
        cleaned = [
            l for l in lines if not any(x in l for x in ["IMPORTANT:", "===Variation"])
        ]
        result = "\n".join(cleaned).strip()
        if multi:
            parts = re.split(r"===\s*Variation\s*\d+\s*===", result)
            st.session_state.generated_variations = [
                p.strip() for p in parts if p.strip()
            ]
        else:
            st.session_state.generated_variations = [result]

    if st.session_state.generated_variations:
        opts = st.session_state.generated_variations
        if multi and len(opts) > 1:
            st.markdown("#### ✨ Reply Options:")
            for idx, text in enumerate(opts, 1):
                st.text_area(f"Version {idx}", value=text, height=100, key=f"rv{idx}")
            choice = st.radio(
                "Select version to send:",
                [f"Version {i}" for i in range(1, len(opts) + 1)],
            )
            sel = int(choice.split()[-1]) - 1
        else:
            st.markdown("#### ✨ Generated Reply:")
            st.text_area("Reply", value=opts[0], height=150, key="rv0")
            sel = 0
        if st.button("Send Email"):
            reply_body = opts[sel]
            payload = {
                "to": em.get("from"),
                "subject": em.get("subject"),
                "body": reply_body,
                "id": em.get("id"),
                "threadId": em.get("threadId"),
            }
            r = requests.post(
                f"http://{ip_address}:8101/email/send",
                json=payload,
                cookies=get_all_cookies(),
            )
            if r.status_code == 200:
                st.success(f"✅ Reply sent to {em.get('from')}!")
            else:
                st.error(f"❌ Failed: {r.status_code} - {r.text}")
    if st.button(
        "Clear Selection",
        key="clr",
        on_click=lambda: st.session_state.pop("selected_email", None),
    ):
        st.experimental_rerun()

st.markdown("---")

# Compose new email
st.subheader("📝 Compose New Email")

to_address = st.text_input("📬 To", placeholder="recipient@example.com")
email_subject = st.text_input("📝 Subject", placeholder="Meeting Follow-up")
compose_content = st.text_area(
    "✍️ What's this email about?", placeholder="Your idea or points to cover..."
)
sign_off_compose = st.text_input(
    "Your sign-off name:", placeholder="e.g. Jerome", key="compose_signoff"
)
if not sign_off_compose:
    sign_off_compose = "Jerome"
compose_instructions = st.text_input(
    "Additional instructions (optional):", placeholder="e.g. more formal"
)
compose_tone = st.radio(
    "Choose tone:", ["Professional", "Friendly", "Concise"], key="compose_tone"
)
compose_variation = st.checkbox("Generate multiple variations", key="compose_multi")

if st.button("🪄 Generate Email"):
    if not to_address.strip():
        st.warning("Please enter recipient address.")
    elif not email_subject.strip():
        st.warning("Please enter subject.")
    elif not compose_content.strip():
        st.warning("Please provide content.")
    else:
        if compose_variation:
            prompt = f"""
You are an assistant that writes professional emails.

IMPORTANT: Only output final emails.
Subject: "{email_subject}"
Content: "{compose_content}"
Instructions: "{compose_instructions}"
Generate 3 {compose_tone.lower()} variations labeled:
===Variation 1===
===Variation 2===
===Variation 3===
Each must:
1. Start with greeting
2. End with "Best regards," then on the next line "{sign_off_compose}"
"""
        else:
            prompt = f"""
You are an assistant that writes professional emails.

IMPORTANT: Only output final email.
Subject: "{email_subject}"
Content: "{compose_content}"
Instructions: "{compose_instructions}"
Generate one {compose_tone.lower()} email:
1. Start with greeting
2. End with "Best regards," then on the next line "{sign_off_compose}"
"""
        response = llm.invoke(prompt)
        out = response.content.strip()
        lines = out.splitlines()
        cleaned = [
            l for l in lines if not any(x in l for x in ["IMPORTANT:", "===Variation"])
        ]
        result = "\n".join(cleaned).strip()
        if compose_variation:
            parts = re.split(r"===\s*Variation\s*\d+\s*===", result)
            st.session_state.generated_compose_variations = [
                p.strip() for p in parts if p.strip()
            ]
        else:
            st.session_state.generated_compose_variations = [result]

# Display compose drafts
if st.session_state.get("generated_compose_variations"):
    drafts = st.session_state["generated_compose_variations"]
    st.markdown("#### ✨ AI-Generated Draft(s)")
    for i, d in enumerate(drafts, 1):
        st.text_area(f"Draft {i}", value=d, height=180, key=f"cd{i}")
    if len(drafts) > 1:
        choice = st.radio(
            "Select draft to send:", [f"Draft {i}" for i in range(1, len(drafts) + 1)]
        )
        sel = int(choice.split()[-1]) - 1
    else:
        sel = 0
    if st.button("Send Composed Email"):
        body = drafts[sel]
        r = requests.post(
            f"http://{ip_address}:8101/email/send",
            json={"to": to_address, "subject": email_subject, "body": body},
            cookies=get_all_cookies(),
        )
        if r.status_code == 200:
            st.success(f"✅ Email sent to {to_address}!")
        else:
            st.error(f"❌ Failed: {r.status_code} - {r.text}")
