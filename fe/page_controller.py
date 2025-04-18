# conda activate MailMate && streamlit run page_controller.py
# streamlit run page_controller.py
# cd be, ./dev.sh

import streamlit as st


Login = st.Page(
    page="views/login.py",
    title="Login Page",
    icon="🔑",
    default=True,
)
Inbox_Summary = st.Page(
    page="views/inbox_summary.py",
    title="Inbox Summary",
    icon="📨",
)
Smart_Replies = st.Page(
    page="views/smart_replies.py",
    title="Smart Replies",
    icon="✉️",
)
Search_Emails = st.Page(
    page="views/search_emails.py",
    title="Search Emails",
    icon="🔍",
)
Calendar_Sync = st.Page(
    page="views/calendar_sync.py",
    title="Calendar Sync",
    icon="📅",
)
Virtual_Assistant = st.Page(
    page="views/virtual_assistant.py",
    title="Virtual Assistant",
    icon="🎙️",
)


pg = st.navigation(
    pages=[
        Login,
        Inbox_Summary,
        Smart_Replies,
        Search_Emails,
        Calendar_Sync,
        Virtual_Assistant,
    ]
)

pg.run()
