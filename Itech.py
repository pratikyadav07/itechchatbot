import streamlit as st
import json
from datetime import datetime
from pathlib import Path
from google import genai

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="I-tech Admission Assistant",
    page_icon="🤖",
    layout="wide"
)

# ---------------- GEMINI API KEY LOAD ----------------
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("❌ GEMINI_API_KEY not found. Please add it to Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "models/gemini-flash-lite-latest"

# ---------------- FILE & FOLDER PATHS ----------------
DATA_DIR = Path("data")
KB_FILE = DATA_DIR / "knowledge_base.json"
DATA_DIR.mkdir(exist_ok=True)

# ---------------- KNOWLEDGE BASE LOAD ----------------
def load_knowledge_base():
    if KB_FILE.exists():
        with open(KB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ---------------- COURSE SEARCH HELPER ----------------
def get_selected_course(kb, course_name):

    for c in kb.get("degree_courses", []):
        if c["name"].lower() == course_name.lower():
            c["course_type"] = "Degree Course"
            return c

    for c in kb.get("career_courses", []):
        if c["name"].lower() == course_name.lower():
            c["course_type"] = "Career Course"
            return c

    return None

# ---------------- LANGUAGE DETECTION ----------------
def detect_language(text: str) -> str:
    text = text.lower()

    hinglish_words = [
        "kya", "kaise", "kyu", "kyon", "hai", "hain", "nahi",
        "batao", "fees", "kitna", "course", "eligibility"
    ]

    for word in hinglish_words:
        if f" {word} " in f" {text} ":
            return "hinglish"

    return "english"

# ---------------- SYSTEM PROMPT ----------------
def create_system_prompt(kb, selected_course=None, reply_language="english"):
    prompt = f"""
You are a SENIOR ADMISSION COUNSELOR at {kb.get("institute_name", "I-tech")}.

LANGUAGE RULE:
- If user asks in English → reply in clear professional English
- If user asks in Hinglish/Hindi-English → reply in friendly Hinglish
- Do NOT mix languages unnecessarily

COMMUNICATION RULES:
- Be polite and student-friendly
- Explain concepts clearly, don’t just paste data
"""

    if reply_language == "hinglish":
        prompt += "\nReply strictly in Hinglish."
    else:
        prompt += "\nReply strictly in English."

    if selected_course:
        prompt += f"""

SELECTED COURSE:
Name: {selected_course.get("name")}
Type: {selected_course.get("course_type")}
Duration: {selected_course.get("duration")}
Eligibility: {selected_course.get("eligibility")}
Fees: {selected_course.get("fee")}

IMPORTANT:
- Student syllabus UI me already dekh raha hai
- Degree Course → semester-wise explain
- Career Course → topic-wise explain
"""

    return prompt

# ---------------- AI RESPONSE FUNCTION ----------------
def get_ai_response(user_msg, chat_history, kb):

    user_language = detect_language(user_msg)

    selected_course_name = st.session_state.get("selected_course")
    selected_course = (
        get_selected_course(kb, selected_course_name)
        if selected_course_name else None
    )

    system_prompt = create_system_prompt(
        kb,
        selected_course,
        reply_language=user_language
    )

    convo = system_prompt + "\n\n"

    for msg in chat_history[-4:]:
        convo += f"{msg['role'].upper()}: {msg['content']}\n"

    convo += f"USER: {user_msg}\nASSISTANT:"

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=convo,
            config={
                "temperature": 0.4,
                "max_output_tokens": 600
            }
        )
        return response.text

    except Exception as e:
        return f"❌ AI Error: {str(e)}"

# ---------------- MAIN UI ----------------
def main():

    st.title("🤖 I-tech Admission & Student Support Chatbot")

    kb = load_knowledge_base()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "selected_course" not in st.session_state:
        st.session_state.selected_course = None

    course_type = st.selectbox(
        "🎯 Select Course Category",
        ["-- Select --", "🎓 Degree Course", "💼 Career Course"]
    )

    if course_type == "🎓 Degree Course":
        degree_courses = [c["name"] for c in kb.get("degree_courses", [])]
        selected = st.selectbox(
            "🎓 Select Degree Course",
            ["-- Select Degree Course --"] + degree_courses
        )
        st.session_state.selected_course = None if selected.startswith("--") else selected

    elif course_type == "💼 Career Course":
        career_courses = [c["name"] for c in kb.get("career_courses", [])]
        selected = st.selectbox(
            "💼 Select Career Course",
            ["-- Select Career Course --"] + career_courses
        )
        st.session_state.selected_course = None if selected.startswith("--") else selected
    else:
        st.session_state.selected_course = None

    if st.session_state.selected_course:
        course = get_selected_course(kb, st.session_state.selected_course)

        if course:
            st.markdown("### 📘 Course Details")
            st.write(f"**Course Name:** {course.get('name')}")
            st.write(f"**Course Type:** {course.get('course_type')}")
            st.write(f"**Duration:** {course.get('duration', 'As per institute')}")
            st.write(f"**Eligibility:** {course.get('eligibility', 'As per institute')}")
            st.write(f"**Fees:** {course.get('fee', 'Contact institute')}")

    st.markdown("---")

    if not st.session_state.chat_history:
        st.info(
            "👋 Welcome to I-tech!\n\n"
            "Ask about:\n"
            "- Course details\n"
            "- Fees & duration\n"
            "- Placement & scope\n"
            "- Syllabus explanation"
        )

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Ask your doubt here...")

    if user_input and user_input.strip():

        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input,
            "time": datetime.now().isoformat()
        })

        with st.spinner("Counselor is thinking..."):
            reply = get_ai_response(
                user_input,
                st.session_state.chat_history[:-1],
                kb
            )

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": reply,
            "time": datetime.now().isoformat()
        })

        st.rerun()

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    main()