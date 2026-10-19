import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import base64

# --- Page Setup & Mobile Layout ---
st.set_page_config(
    page_title="FriendChat",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Mobile-focused CSS styling
st.markdown("""
<style>
    /* Full mobile container feeling */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
        max-width: 600px;
    }
    
    /* Chat bubbles */
    .chat-bubble {
        padding: 10px 14px;
        border-radius: 16px;
        margin-bottom: 10px;
        max-width: 82%;
        font-size: 0.95rem;
        line-height: 1.4;
        word-break: break-word;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .chat-bubble.mine {
        background-color: #007aff;
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }
    .chat-bubble.others {
        background-color: #f1f0f0;
        color: #1a1a1a;
        margin-right: auto;
        border-bottom-left-radius: 4px;
    }
    .chat-meta {
        font-size: 0.72rem;
        margin-bottom: 3px;
        opacity: 0.85;
    }
    .chat-meta.mine {
        text-align: right;
        color: #e0e0e0;
    }
    .chat-meta.others {
        text-align: left;
        color: #777;
    }
    
    /* Floating action buttons */
    .stButton>button {
        border-radius: 20px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Auto-refresh chat feed every 4 seconds to receive friends' new messages
st_autorefresh(interval=4000, key="chat_autorefresh")

# --- Google Sheets Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_messages():
    """Fetch all chat rows from Google Sheets."""
    try:
        df = conn.read(ttl="2s")
        if df is None or df.empty:
            return pd.DataFrame(columns=["timestamp", "sender", "message", "media_type", "media_data"])
        return df.fillna("")
    except Exception:
        return pd.DataFrame(columns=["timestamp", "sender", "message", "media_type", "media_data"])

def save_message(sender: str, message: str, media_type: str = "", media_data: str = ""):
    """Append a new chat message into Google Sheets."""
    df_existing = load_messages()
    new_entry = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sender": sender,
        "message": message,
        "media_type": media_type,
        "media_data": media_data
    }])
    updated_df = pd.concat([df_existing, new_entry], ignore_index=True)
    conn.update(data=updated_df)

# --- User Session Setup ---
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

# Login / Name prompt if not set
if not st.session_state.user_name:
    st.title("👋 Welcome to FriendChat")
    st.write("Enter your name to start chatting with friends.")
    
    with st.form("name_form"):
        name_input = st.text_input("Your Display Name", placeholder="e.g. Alex")
        if st.form_submit_button("Join Chat", use_container_width=True):
            if name_input.strip():
                st.session_state.user_name = name_input.strip()
                st.rerun()
            else:
                st.error("Please enter a name.")
    st.stop()

# --- Main Chat Header ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown(f"### 💬 FriendChat (`{st.session_state.user_name}`)")
with col_head2:
    if st.button("Change Name", use_container_width=True):
        st.session_state.user_name = ""
        st.rerun()

st.divider()

# --- Message Feed Display ---
messages_df = load_messages()

chat_box = st.container()
with chat_box:
    if messages_df.empty:
        st.info("No messages yet. Say hi to your friends!")
    else:
        for _, row in messages_df.iterrows():
            sender = str(row.get("sender", ""))
            text = str(row.get("message", ""))
            ts = str(row.get("timestamp", ""))[-8:] # HH:MM:SS
            mtype = str(row.get("media_type", ""))
            mdata = str(row.get("media_data", ""))
            
            is_mine = (sender == st.session_state.user_name)
            bubble_class = "mine" if is_mine else "others"

            # Sender & Time
            st.markdown(
                f'<div class="chat-meta {bubble_class}"><strong>{sender}</strong> • {ts}</div>',
                unsafe_allow_html=True
            )

            # Bubble container
            bubble_html = f'<div class="chat-bubble {bubble_class}">'
            if text:
                bubble_html += f'<div>{text}</div>'
            bubble_html += '</div>'
            st.markdown(bubble_html, unsafe_allow_html=True)

            # Display Media (Images / Videos)
            if mtype == "image" and mdata:
                try:
                    img_bytes = base64.b64decode(mdata)
                    st.image(img_bytes, width=280)
                except Exception:
                    st.caption("⚠️ Could not load image")
            elif mtype == "video" and mdata:
                try:
                    vid_bytes = base64.b64decode(mdata)
                    st.video(vid_bytes)
                except Exception:
                    st.caption("⚠️ Could not load video")

# --- Send Message & Media Input Bar ---
st.markdown("---")
with st.expander("📎 Attach Photo or Video", expanded=False):
    uploaded_file = st.file_uploader(
        "Upload from gallery/camera",
        type=["png", "jpg", "jpeg", "mp4", "mov"],
        label_visibility="collapsed"
    )

with st.form("chat_input_form", clear_on_submit=True):
    col_input, col_send = st.columns([4, 1])
    with col_input:
        user_message = st.text_input("Type a message...", placeholder="Type here...", label_visibility="collapsed")
    with col_send:
        submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted:
        media_type = ""
        media_data = ""

        # Process media upload if provided
        if uploaded_file is not None:
            file_mime = uploaded_file.type
            bytes_data = uploaded_file.read()
            # Convert file to base64 string to store easily in Google Sheets
            media_data = base64.b64encode(bytes_data).decode("utf-8")
            if "image" in file_mime:
                media_type = "image"
            elif "video" in file_mime:
                media_type = "video"

        # Validate that user provided either text or media
        if user_message.strip() or media_data:
            with st.spinner("Sending..."):
                save_message(
                    sender=st.session_state.user_name,
                    message=user_message.strip(),
                    media_type=media_type,
                    media_data=media_data
                )
            st.rerun()
        else:
            st.warning("Please type a message or select a file.")