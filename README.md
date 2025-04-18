# MailMate

# Smart Email Assistant (Streamlit SaaS)

The **Smart Email Assistant** is a voice- and text-enabled Streamlit-based SaaS platform designed to supercharge your email productivity using LLMs. It combines AI-powered summarization, smart replies, semantic search, calendar syncing, email tracking, and virtual assistant capabilities into one streamlined tool.

---

## 🚀 Features

### 📨 Inbox Summary

- Summarizes your email threads using LLMs.
- Filters emails by priority: High, Medium, Low.
- Displays action items, senders, and timestamps.
- Quick reply and calendar integration options.

### ✉️ Smart Replies

- Generate AI-powered replies with selectable tone: Professional, Friendly, or Concise.
- Option to generate multiple reply variations.
- One-click send or manual edit supported.

### 🔍 Search Emails

- Natural language search over your emails (e.g., "What did John say about the report?").
- Filter results by sender, sentiment, date, and keywords.
- View or take quick actions (reply, calendar, etc.).

### 📅 Calendar Sync

- Detects meeting details from emails.
- Allows users to add events directly to Google Calendar.
- Displays source email info and lets users edit or dismiss event suggestions.

### 📈 Email Tracker

- Tracks outgoing emails awaiting response.
- Shows how long it’s been since you sent each email.
- Quick options to send follow-ups or mark as resolved.
- Placeholder for analytics like average reply time and response rate.

### 🎙️ Virtual Assistant

- Interact with the assistant via text or **voice input** (using `st.audio_input`).
- Asks questions like "What emails haven’t been replied to?" or "Summarize today’s unread messages."
- Uses LLMs to provide summarized, context-aware answers.

---

## 🛠️ Tech Stack

- **Streamlit** for the web UI
- **Python** for backend logic and routing
- **LLMs** (e.g., OpenAI or local models) for language understanding
- (Optional) **Whisper/OpenAI Audio** for voice transcription
- **Google Calendar API** (planned) for syncing events

---

## 📂 File Structure

```
.
├── page_controller.py           # Main Streamlit router
├── views/
│   ├── inbox_summary.py
│   ├── smart_replies.py
│   ├── search_emails.py
│   ├── calendar_sync.py
│   ├── email_tracker.py
│   └── virtual_assistant.py
└── README.md
```

## 📬 Contact

Interested in contributing or integrating it into your workflow?
Feel free to reach out or fork the project!
