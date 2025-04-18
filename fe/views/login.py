import streamlit as st
from streamlit_javascript import st_javascript
import os
from dotenv import load_dotenv

load_dotenv()
# Page config
st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")

# Sidebar for Google API Key input
st.sidebar.header("🔑 Google API Configuration")
api_key_input = st.sidebar.text_input("Enter your Google API Key", type="password")

# default fallback to localhost
ip_address = os.getenv("IP_ADDRESS", "localhost")

# Store the API key in session state
if api_key_input:
    st.session_state["google_api_key"] = api_key_input
    st.sidebar.success("API Key saved in session.")


def get_all_cookies():
    """
    Returns the cookies as a dictionary using st.context.headers.
    """
    from urllib.parse import unquote

    # Use st.context.headers instead of _get_websocket_headers
    headers = st.context.headers
    # Ensure the cookie header exists (note: header keys are often lowercase)
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


# Styling (optional: adjust padding as needed)
st.markdown(
    """
    <style>
    .centered {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding-top: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Centered UI
st.markdown('<div class="centered">', unsafe_allow_html=True)

# New animated login gif from Giphy
st.image(
    "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExZGhrb3RreHVwczF0M3JtdG91ODFiNGthOWg0ODc4YjZzbXl2dTdiMSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/A2lJK1XdFOUhZl0U0W/giphy.gif",
    width=200,
)

cookie = get_all_cookies()

# If cookies exist, display message to indicate current logged-in state.
if cookie:
    st.success("You are logged in")


# Display login UI title and button regardless of logged in status
st.title("Welcome!")
st.subheader("Please log in to continue")

login = st.button(
    "🔐 Login", key="login", help="Click to log in", use_container_width=True
)

login_url = f"http://{ip_address}:8101/auth/login"

if login:
    st.markdown(
        f'<meta http-equiv="refresh" content="0; URL={login_url}">',
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)
