import logging
import os
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_core.tools import BaseTool

from src.services.email import get_email

logger: logging.Logger = logging.getLogger('uvicorn.error')


def fetch_emails(user_id: str):
    emails_data = get_email(user_id, 10, False, None)

    processed_emails = []
    for email in emails_data:
        # Check for legacy format with "payload"
        if "payload" in email:
            headers = email.get("payload", {}).get("headers", [])
            sender = subject = date_str = None
            for header in headers:
                if header.get("name") == "From":
                    sender = header.get("value")
                elif header.get("name") == "Subject":
                    subject = header.get("value")
                elif header.get("name") == "Date":
                    date_str = header.get("value")
            raw = email.get("raw", "")
        else:
            # New format: keys are at the root level
            sender = email.get("from", "Unknown Sender")
            subject = email.get("subject", "No Subject")
            raw = email.get("raw", "")
            date_str = None

        try:
            date_obj = (
                datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                if date_str
                else datetime.now()
            )
        except Exception:
            date_obj = datetime.now()

        processed_emails.append(
            {
                "id": email.get("id", str(date_obj.timestamp())),
                "subject": subject or "No Subject",
                "sender": sender or "Unknown Sender",
                "summary": raw,
                "priority": (
                    "High" if "IMPORTANT" in email.get(
                        "labelIds", []) else "Low"
                ),
                "date": date_obj,
            }
        )
    return processed_emails


def summarize_emails(emails):
    # Load environment variables
    logger.info("summarising emails %s", emails)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Initialize Gemini LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-001",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        google_api_key=GOOGLE_API_KEY,
    )

    combined = ""
    for email in emails:
        combined += (
            f"From: {email['sender']}\n"
            f"Subject: {email['subject']}\n"
            f"Summary: {email['summary']}\n\n"
        )

    prompt = """
You are an intelligent assistant summarizing an inbox. Below are the details of recent emails:

{email_content}

Please provide a well-structured and concise summary of what these emails are about. Highlight any high-priority messages or actions needed.
"""

    try:
        prompt_template = ChatPromptTemplate.from_template(prompt)
        chain = prompt_template | llm
        response = chain.invoke({"email_content": combined})
        return response.content
    except Exception as e:
        return f"Error generating summary: {e}"


def get_generate_inbox_summary_tool(user_id: str) -> BaseTool:

    @tool
    def generate_inbox_summary() -> str:
        """Fetches recent emails via an API call (using cookies from st.context.headers) and summarizes them using an LLM."""
        emails = fetch_emails(user_id)
        if isinstance(emails, str):
            # Return error message if fetching fails
            return emails
        response = summarize_emails(emails)
        logger.info("generate_inbox_summary response: %s", response)
        return response

    return generate_inbox_summary
