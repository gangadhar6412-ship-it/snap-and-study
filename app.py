import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import streamlit as st

from google import genai
from google.genai import types

from prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE,
    SYLLABUS_PROMPT,
    STUDY_PROGRESS_PROMPT,
    FINAL_REPORT_PROMPT,
    CHAT_PROMPT
)

st.set_page_config(
    page_title="Snap & Study",
    page_icon="📚",
    layout="wide"
)

MODEL_NAME = "gemini-3.8-flash"

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
    GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]

except Exception:
    st.error(
        """
        ❌ Missing secrets.

        Please check:

        .streamlit/secrets.toml

        It must contain:

        GEMINI_API_KEY
        GMAIL_ADDRESS
        GMAIL_APP_PASSWORD
        """
    )
    st.stop()

@st.cache_resource
def get_gemini_client():
    return genai.Client(
        api_key=GEMINI_API_KEY
    )

client = get_gemini_client()

if "started" not in st.session_state:
    st.session_state.started = False

if "student_name" not in st.session_state:
    st.session_state.student_name = ""

if "student_email" not in st.session_state:
    st.session_state.student_email = ""

if "syllabus_uploaded" not in st.session_state:
    st.session_state.syllabus_uploaded = False

if "syllabus_image" not in st.session_state:
    st.session_state.syllabus_image = None

if "study_images" not in st.session_state:
    st.session_state.study_images = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_progress" not in st.session_state:
    st.session_state.last_progress = ""

if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0

def ask_gemini(prompt, image_bytes=None, mime_type=None):
    try:
        parts = [
            types.Part.from_text(
                text=prompt
            )
        ]

        if image_bytes is not None:
            parts.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                )
            )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2
            )
        )

        return response.text

    except Exception as e:
        return f"""
❌ Gemini error:

{str(e)}

Please check your Gemini API key and internet connection.
"""

def add_message(role, content):
    st.session_state.chat_history.append(
        {
            "role": role,
            "content": content
        }
    )

def display_chat():
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(
                message["content"]
            )

def send_email(
    recipient_email,
    subject,
    body
):
    try:
        message = MIMEMultipart()

        message["From"] = GMAIL_ADDRESS
        message["To"] = recipient_email
        message["Subject"] = subject

        message.attach(
            MIMEText(
                body,
                "plain"
            )
        )

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as server:
            server.login(
                GMAIL_ADDRESS,
                GMAIL_APP_PASSWORD
            )

            server.sendmail(
                GMAIL_ADDRESS,
                recipient_email,
                message.as_string()
            )

        return True, "Email sent successfully."

    except Exception as e:
        return False, str(e)

def ask_chat(question):
    context = ""

    if st.session_state.last_progress:
        context += f"""

LATEST STUDY PROGRESS:

{st.session_state.last_progress}
"""

    if st.session_state.chat_history:
        context += """

RECENT CONVERSATION:
"""

        for message in st.session_state.chat_history[-8:]:
            if message["role"] == "user":
                context += (
                    f"\nStudent: {message['content']}"
                )
            else:
                context += (
                    f"\nAssistant: {message['content']}"
                )

    prompt = f"""
{CHAT_PROMPT}

{context}

STUDENT QUESTION:

{question}
"""

    return ask_gemini(prompt)

st.title("📚 Snap & Study")

st.markdown(
    """
### Your AI-powered study progress assistant

**Snap your syllabus → Upload what you studied → Find gaps → Learn → Chat → Track progress**
"""
)

with st.sidebar:
    st.header("📊 Dashboard")

    if st.session_state.student_name:
        st.write(
            f"👨‍🎓 **Student:** {st.session_state.student_name}"
        )

    if st.session_state.student_email:
        st.write(
            f"📧 **Report Email:** {st.session_state.student_email}"
        )

    st.divider()

    if st.session_state.syllabus_uploaded:
        st.success(
            "📋 Syllabus uploaded"
        )
    else:
        st.warning(
            "📋 Syllabus not uploaded"
        )

    st.write(
        f"📸 Study uploads: {len(st.session_state.study_images)}"
    )

    st.write(
        f"💬 Questions: {st.session_state.total_questions}"
    )

    st.divider()

    st.markdown(
        """
### Workflow

1. Enter name + Gmail
2. Upload syllabus
3. Upload study material
4. Find remaining topics
5. Get study content
6. Ask AI questions
7. Upload more material
8. Send final report
"""
    )

if not st.session_state.started:
    st.subheader("👋 Start Snap & Study")

    st.write(
        "Enter your details. Your Gmail is used only as the "
        "destination for the final study report."
    )

    student_name = st.text_input(
        "👨‍🎓 Your Name",
        placeholder="Enter your name"
    )

    student_email = st.text_input(
        "📧 Your Gmail",
        placeholder="example@gmail.com"
    )

    if st.button(
        "🚀 Start",
        type="primary"
    ):
        if not student_name.strip():
            st.error(
                "Please enter your name."
            )

        elif not student_email.strip():
            st.error(
                "Please enter your Gmail."
            )

        elif "@" not in student_email:
            st.error(
                "Please enter a valid email address."
            )

        else:
            st.session_state.student_name = (
                student_name.strip()
            )

            st.session_state.student_email = (
                student_email.strip()
            )

            st.session_state.started = True

            add_message(
                "assistant",
                WELCOME_MESSAGE
            )

            st.rerun()

if st.session_state.started:
    display_chat()

    st.divider()

    if not st.session_state.syllabus_uploaded:
        st.subheader(
            "📋 Step 1 — Upload Your Syllabus"
        )

        syllabus_file = st.file_uploader(
            "Upload a clear syllabus image",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp"
            ],
            key="syllabus_upload"
        )

        if syllabus_file is not None:
            st.image(
                syllabus_file,
                caption="Syllabus",
                width=600
            )

            if st.button(
                "🔍 Analyze Syllabus",
                type="primary"
            ):
                image_bytes = syllabus_file.getvalue()

                with st.spinner(
                    "Reading your syllabus..."
                ):
                    result = ask_gemini(
                        SYLLABUS_PROMPT,
                        image_bytes,
                        syllabus_file.type
                    )

                st.session_state.syllabus_uploaded = True
                st.session_state.syllabus_image = image_bytes

                add_message(
                    "user",
                    "📋 I uploaded my syllabus."
                )

                add_message(
                    "assistant",
                    result
                )

                st.rerun()

    else:
        st.subheader(
            "📸 Step 2 — Upload What You Studied"
        )

        st.info(
            """
Upload photos of your notes, textbook pages,
handwritten material, diagrams or solved problems.
"""
        )

        study_file = st.file_uploader(
            "Upload study material",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp"
            ],
            key=f"study_upload_{len(st.session_state.study_images)}"
        )

        if study_file is not None:
            st.image(
                study_file,
                caption="Study material",
                width=600
            )

            if st.button(
                "📊 Check My Progress",
                type="primary"
            ):
                image_bytes = study_file.getvalue()

                with st.spinner(
                    "Comparing your study material with the syllabus..."
                ):
                    result = ask_gemini(
                        STUDY_PROGRESS_PROMPT,
                        image_bytes,
                        study_file.type
                    )

                st.session_state.study_images.append(
                    image_bytes
                )

                st.session_state.last_progress = result

                add_message(
                    "user",
                    "📸 I uploaded study material."
                )

                add_message(
                    "assistant",
                    result
                )

                st.rerun()

    if st.session_state.syllabus_uploaded:
        st.divider()

        st.subheader(
            "💬 Ask About Your Topics"
        )

        st.write(
            """
Ask questions about your remaining or partially covered
topics without leaving the application.
"""
        )

        st.markdown(
            """
**Try:**

- Explain this topic simply.
- Teach me this step by step.
- Give me an example.
- Give me 5 practice questions.
- Explain this like a beginner.
- What should I study first?
"""
        )

        question = st.chat_input(
            "Ask your AI study assistant..."
        )

        if question:
            st.session_state.total_questions += 1

            add_message(
                "user",
                question
            )

            with st.spinner(
                "Thinking..."
            ):
                answer = ask_chat(
                    question
                )

            add_message(
                "assistant",
                answer
            )

            st.rerun()

    if st.session_state.syllabus_uploaded:
        st.divider()

        st.subheader(
            "📧 Final Study Report"
        )

        st.write(
            f"""
Your report will be sent to:

**{st.session_state.student_email}**
"""
        )

        if st.button(
            "📧 Generate & Send Final Report",
            type="primary"
        ):
            with st.spinner(
                "Creating your final study report..."
            ):
                report = ask_gemini(
                    FINAL_REPORT_PROMPT
                )

            success, message = send_email(
                st.session_state.student_email,
                "📚 Snap & Study - Final Study Report",
                report
            )

            if success:
                st.success(
                    "✅ Report sent successfully to your Gmail!"
                )

                with st.expander(
                    "📄 View Final Report"
                ):
                    st.markdown(
                        report
                    )

            else:
                st.error(
                    f"❌ Email could not be sent: {message}"
                )

                with st.expander(
                    "📄 View Report Anyway"
                ):
                    st.markdown(
                        report
                    )

st.divider()

st.caption(
    "📚 Snap & Study — Know what you studied. Know what remains."
)