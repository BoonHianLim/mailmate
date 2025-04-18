import json
import logging
import os
import re
from src.services.email import get_email
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

logger: logging.Logger = logging.getLogger('uvicorn.error')


def generate_keywords(query):
    """
    Uses the LLM to extract keywords from the user's query.
    The LLM returns a comma-separated list of keywords.
    """
    # Load environment variables
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

    prompt = f"""
Extract keywords from the following user query for email search.
Return the keywords as a comma-separated list.
User Query: "{query}"
"""
    try:
        response = llm.invoke(prompt)
        keywords_str = response.content.strip()
        keywords_list = [kw.strip()
                         for kw in keywords_str.split(",") if kw.strip()]
        return keywords_list
    except Exception as e:
        return []


def search_emails_llm(emails, query):
    """
    Uses the LLM to filter and return only the emails that match the query.
    Returns the results as a JSON array (a Python list of dictionaries).
    """
    # Load environment variables
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

    email_summaries = ""

    if not emails or isinstance(emails, str):
        return ""  # Return an empty list if no emails were fetched

    for i, email in enumerate(emails):
        from_field = email.get("from", "Unknown Sender")
        subject = email.get("subject", "No Subject")
        date_str = email.get("date", "Unknown")
        content = email.get("raw")
        if content is None:
            content = email.get("snippet", "No content available.")
        email_summaries += (
            f"[Email {i+1}]\nFrom: {from_field}\nSubject: {subject}\nDate: {date_str}\n"
            f"Content: {content}\n\n"
        )

    prompt = """
    You are a smart assistant that searches through a user's inbox.

    Your job is to carefully examine each email and return only those that match the user's query.

    ---

    **Inbox Emails:**
    {email_summaries}

    ---

    **User Query:**
    "{query}"

    ---

    **Instructions:**

    1. Carefully read each email.
    2. Return only the emails that clearly match the intent of the query.
    3. If no email matches, return an empty list: `[]`

    Return the results as a Python list of dictionaries with the following fields:
    - "Subject"
    - "Sender"
    - "Date"
    - "Summary"

    Example output format:
    [
    {{
        "Subject": "Project Update",
        "Sender": "John <john@example.com>",
        "Date": "Fri, 29 Mar 2024 15:00:00 +0000",
        "Summary": "We're ahead of schedule for Q2 and should be done by mid-April."
    }}
    ]
    Please output ONLY the JSON array with no additional text.
    """

    try:
        prompt_template = ChatPromptTemplate.from_template(prompt)
        chain = prompt_template | llm
        response = chain.invoke(
            {"email_summaries": email_summaries, "query": query})
        return response.content
    except Exception as e:
        raise e


def get_search_emails_tool(user_id: str) -> BaseTool:

    @tool
    def search_emails_tool(query: str) -> str:
        """
        Searches the user's emails via an API call using cookies from st.context.headers.
        Returns the search results as a JSON array (a Python list of dictionaries).
        """
        keywords = generate_keywords(query)
        emails = get_email(user_id, 10, True, keywords)
        logger.info("Fetched emails: %s", emails)
        result = search_emails_llm(emails, query)
        cleaned_output = re.sub(r"```(?:json|python)?",
                                "", result).strip("` \n")
        json_string = json.dumps(cleaned_output)
        escaped_json = json_string.replace("{", "{{").replace("}", "}}")
        return escaped_json

    return search_emails_tool
