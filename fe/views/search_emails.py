from dotenv import load_dotenv
import streamlit as st
import json
import pandas as pd
import ast
import re
import os
import requests
from datetime import date
from urllib.parse import quote_plus, unquote
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

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

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-001",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=GOOGLE_API_KEY,
)

# Set up Streamlit page
st.set_page_config(page_title="Search Emails", page_icon="🔍")
st.title("🔍 Search Emails")


def get_all_cookies():
    """
    Returns the cookies as a dictionary using st.context.headers.
    """
    headers = st.context.headers  # Use st.context.headers as per your reference
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


def generate_keywords(query):
    """
    Uses the LLM to extract keywords from the user's query.
    The LLM returns a comma-separated list of keywords.
    """
    prompt = f"""
Extract keywords from the following user query for email search.
Return the keywords as a comma-separated list.
User Query: "{query}"
"""
    try:
        response = llm.invoke(prompt)
        keywords_str = response.content.strip()
        # Split by comma and filter out empty strings
        keywords_list = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
        return keywords_list
    except Exception as e:
        st.error(f"Error generating keywords: {e}")
        return []


def fetch_emails(query):
    """
    Generates keywords from the query and builds the API URL.
    Calls the email API with cookies and returns the email data.
    """
    keywords = generate_keywords(query)
    base_url = f"http://{ip_address}:8101/email?includeRead=true"
    for kw in keywords:
        base_url += f"&q={quote_plus(kw)}"
    cookies = get_all_cookies()
    cookies_request = {"key": cookies.get("key", "")}
    try:
        response = requests.get(base_url, cookies=cookies_request)
        response.raise_for_status()
        data = response.json()
        # The API returns a dict with a 'message' key containing the email array; fallback if not present.
        if isinstance(data, dict) and "message" in data:
            emails = data["message"]
        else:
            emails = data
        return emails
    except Exception as e:
        st.error(f"Failed to fetch emails from API: {e}")
        return []


def search_emails_llm(
    emails,
    query,
    sender=None,
    sentiment=None,
    start_date=None,
    end_date=None,
    keywords=None,
):
    # Build the email summaries for context; if no emails are provided, return early.
    email_summaries = ""
    if not emails:
        return "No emails match your query.", "[]"

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

    # Define clear delimiter markers in the prompt
    prompt = f"""
You are a smart assistant that searches through a user's inbox.

Your task is to perform a two-step action in one response:

Step 1: Read the inbox emails provided below and apply the following filters:
- Include only emails that clearly match the user's query.
- If filters such as Sender, Sentiment, Date Range, or Keywords are provided, apply them strictly.
- Completely ignore unrelated or off-topic emails.
Then, provide a concise natural language summary that directly answers the user's query.
You may reference relevant email details (subject, sender, date) in your summary.

Step 2: From the filtered emails, construct a JSON array of dictionaries.
Each dictionary should represent one email and have exactly the following keys:
- "Subject"
- "Sender"
- "Date"
- "Summary"

If there are no matching emails, the JSON array should be [].

Please follow this exact output format with the specified delimiters:

Summary:
<your natural language answer here>
--END SUMMARY--
JSON:
<your JSON array here (must be a valid Python list)>
--END JSON--

Here are the inbox emails:
{email_summaries}

User Query:
"{query}"

Filters:
- Sender: {sender or "Any"}
- Sentiment: {sentiment or "Any"}
- Date Range: {start_date or "Any"} to {end_date or "Any"}
- Keywords: {keywords or "None"}
"""
    try:
        response = llm.invoke(prompt)
        output = response.content.strip()
        # For debugging, you could uncomment the next line to see the raw output.
        # st.write("LLM Raw Output:", output)

        # Split the output based on the defined delimiters.
        summary_text = ""
        json_text = ""

        # Find the boundaries using regex or simple string splitting.
        if "Summary:" in output and "--END SUMMARY--" in output:
            summary_text = (
                output.split("Summary:")[1].split("--END SUMMARY--")[0].strip()
            )
        if "JSON:" in output and "--END JSON--" in output:
            json_text = output.split("JSON:")[1].split("--END JSON--")[0].strip()

        # Fallback for json_text if it was not captured.
        if not json_text:
            json_text = "[]"
        return summary_text, json_text
    except Exception as e:
        return f"Error during LLM search: {e}", "[]"


# UI inputs
query = st.text_input(
    "Ask a question or search your emails:",
    placeholder="e.g. What did John say about the quarterly report?",
)

with st.expander("🔧 Advanced Filters"):
    col1, col2 = st.columns(2)
    with col1:
        sender = st.text_input("Sender", placeholder="e.g. john@company.com")
        sentiment = st.selectbox(
            "Sentiment", ["Any", "Positive", "Neutral", "Negative"]
        )
    with col2:
        start_date = st.date_input("Start Date", value=None)
        end_date = st.date_input("End Date", value=None)
    keywords = st.text_input("Keywords", placeholder="e.g. budget, deadline, proposal")

# Search action
if st.button("Search"):
    st.markdown("---")
    st.subheader("📬 Search Results")
    with st.spinner("Querying your inbox..."):
        emails = fetch_emails(query)
        summary_text, json_output = search_emails_llm(
            emails=emails,
            query=query,
            sender=sender if sender else None,
            sentiment=sentiment if sentiment != "Any" else None,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None,
            keywords=keywords if keywords else None,
        )
    # Display the natural language summary.
    st.markdown(summary_text)

    # Provide an expander for the table view of the JSON emails.
    with st.expander("Show detailed emails (table view)"):
        try:
            # Attempt to parse the JSON portion into a Python list.
            parsed_data = ast.literal_eval(json_output)
            if isinstance(parsed_data, list) and all(
                isinstance(item, dict) for item in parsed_data
            ):
                df = pd.DataFrame(parsed_data)
                st.table(df)
            else:
                st.warning("Unexpected data format in JSON output.")
                st.markdown(f"```markdown\n{json_output}\n```")
        except Exception as e:
            st.warning(f"Error parsing JSON output: {e}")
            st.markdown(f"```markdown\n{json_output}\n```")

st.markdown("---")
st.caption(
    "Use natural language or combine with filters to pinpoint what you're looking for."
)
