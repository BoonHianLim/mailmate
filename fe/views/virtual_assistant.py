import streamlit as st
from urllib.parse import unquote
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()
ip_address = os.getenv("IP_ADDRESS", "127.0.0.1")  # default fallback to localhost

st.set_page_config(page_title="Virtual Assistant", layout="centered")

st.title("🎙️ Virtual Assistant")

# Description Section
st.markdown("### 💡 What can this assistant do?")
st.markdown(
    """
    - 📬 **Summarize your inbox**: Get concise overviews of unread or important emails.
    - 🔍 **Search your emails**: Use natural language to find specific conversations.
    - 🎤 **Talk or type**: Interact with the assistant via voice or text input.
    """
)

st.markdown("---")

redirect = st.button(
    "🚀 Redirect Me", key="redirect", help="Click to log in", use_container_width=True
)


# Handle Cookies
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


cookies = get_all_cookies()
key = cookies.get("key")

if redirect and key:
    target_url = f"http://{ip_address}:12393?auth_uid={key}"
    st.markdown(
        f'<meta http-equiv="refresh" content="0; URL={target_url}">',
        unsafe_allow_html=True,
    )
elif redirect:
    st.error("Cookie named 'key' not found. Please ensure it's set in your browser.")

st.markdown("---")
st.caption(
    "Try asking things like *'Summarize today's unread emails'* or *'Find emails from Alice last week'*."
)
