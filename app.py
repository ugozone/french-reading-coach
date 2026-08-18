import os
import tempfile
from datetime import datetime

import streamlit as st
from gtts import gTTS
from auth import get_current_user, render_auth_sidebar
from teacher_texts import TEACHER_TEXTS
from db import (
    ensure_all_seeded,
    create_or_get_student,
    find_student_by_email_or_name,
    get_student,
    get_all_students,
    get_lesson_id_for_text,
    save_attempt_to_db,
    get_progress_rows,
    get_attempt_history,
    get_phrase_history,
    get_grammar_lessons,
    get_grammar_questions,
    save_grammar_attempt,
    update_grammar_progress,
    get_grammar_progress,
    get_grammar_attempt_summary,
    get_guided_reading_tasks,
    get_guided_reading_sections,
    create_guided_reading_attempt,
    save_guided_section_attempt,
    finalize_guided_reading_attempt,
    get_guided_reading_attempt_status,
    get_guided_reading_attempt_overview,
    get_guided_reading_attempt_details,
    get_latest_in_progress_guided_attempt,
    get_guided_completed_section_count,
    normalize_simple,
    is_teacher_name,
    is_teacher_email,
    get_teacher_access_record,
    get_teacher_profile_by_email,
    get_teacher_display_name,
    assign_reading_task,
    get_assignments_for_student,
    get_all_assignments_overview,
    get_student_learning_activity,
    get_all_learning_activity,
    mark_assignment_started,
    mark_assignment_completed,
    create_guided_task,
    create_guided_task_from_teacher_text,
    upload_teacher_audio,
)
from speech import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    pronunciation_score,
    word_feedback,
    detect_liaison_candidates,
    transcribe_audio_file,
    generate_coaching_message,
    detect_attempt_issue,
    phonetic_transcription,
    analyze_speech_acoustics,
)
from ui_helpers import (
    make_lesson_label,
    render_lesson_card,
    render_coaching_message,
    render_colored_feedback_with_ipa,
    render_pronunciation_focus,
)
from research import (
    RESEARCH_APPROVAL_REFERENCE,
    RESEARCH_CONSENT_TEXT,
    RESEARCH_CONSENT_VERSION,
    enroll_participant,
    get_research_admin_summary,
    get_research_state,
    is_research_admin,
    leave_research_session,
    log_research_event,
    research_enabled,
    research_status,
    rows_to_csv,
    submit_beta_feedback,
)

MAX_PHRASE_ATTEMPTS = 10
DEFAULT_TEXT = "Bonjour, comment allez-vous aujourd'hui ?"

st.set_page_config(page_title="French Reading Coach — Public Beta", page_icon="🇫🇷", layout="wide")

st.markdown("""
<style>
:root {
    --bg: #f7f2ea;
    --surface: #fffaf3;
    --surface-strong: #ffffff;
    --text: #2b1d14;
    --muted: #6b5748;
    --line: #e7d8c7;
    --brand: #8b5e34;
    --brand-2: #d4a017;
    --shadow: 0 10px 28px rgba(60, 35, 15, 0.10);
    --radius: 18px;
}
.stApp {
    background:
        radial-gradient(circle at top left, rgba(212,160,23,0.10), transparent 28%),
        radial-gradient(circle at top right, rgba(139,94,52,0.10), transparent 26%),
        linear-gradient(180deg, #fffaf5 0%, var(--bg) 100%);
    color: var(--text);
}
.block-container {
    max-width: 1200px;
    padding-top: 1rem;
    padding-bottom: 2rem;
}
h1, h2, h3, h4 { color: var(--text); letter-spacing: -0.02em; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2f1e12 0%, #3d2818 100%);
    border-right: 1px solid rgba(212,160,23,0.18);
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
    color: #f7e7ce !important;
}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    color: #2b1d14 !important;
    -webkit-text-fill-color: #2b1d14 !important;
    caret-color: #8b5e34 !important;
    background: #fffaf3 !important;
    border: 1px solid #d7c2a8 !important;
    border-radius: 14px !important;
}
section[data-testid="stSidebar"] input::placeholder,
section[data-testid="stSidebar"] textarea::placeholder {
    color: #8a7666 !important;
    opacity: 1 !important;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: #fffaf3 !important;
    border: 1px solid #d7c2a8 !important;
    border-radius: 14px !important;
    color: #2b1d14 !important;
}
.stTextInput input,
.stTextArea textarea,
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    border-radius: 14px !important;
    border: 1px solid #dcc8b2 !important;
    background: rgba(255,250,243,0.96) !important;
    color: #2b1d14 !important;
    -webkit-text-fill-color: #2b1d14 !important;
}
.stButton > button {
    border: none !important;
    border-radius: 14px !important;
    padding: 0.72rem 1.1rem !important;
    font-weight: 700 !important;
    color: white !important;
    background: linear-gradient(90deg, #8b5e34 0%, #d4a017 100%) !important;
    box-shadow: 0 8px 20px rgba(139,94,52,0.22) !important;
}
.stButton > button:hover { opacity: 0.96; transform: translateY(-1px); }
button[data-baseweb="tab"] { border-radius: 14px 14px 0 0 !important; font-weight: 700 !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #8b5e34 !important; }
div[data-testid="metric-container"] {
    background: var(--surface-strong);
    border: 1px solid var(--line);
    padding: 18px;
    border-radius: 18px;
    box-shadow: var(--shadow);
}
div[data-testid="stDataFrame"] {
    background: var(--surface-strong);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 0.35rem;
    box-shadow: var(--shadow);
}
details {
    background: var(--surface-strong);
    border: 1px solid var(--line);
    border-radius: 16px;
    box-shadow: var(--shadow);
    overflow: hidden;
}
summary { padding: 0.9rem 1rem !important; font-weight: 700 !important; }
.jami-hero {
    background:
        radial-gradient(circle at top right, rgba(255,240,210,0.22), transparent 30%),
        linear-gradient(100deg, #6f4a2a 0%, #d4a017 100%);
    color: white;
    padding: 28px;
    border-radius: 24px;
    box-shadow: 0 16px 40px rgba(111,74,42,0.22);
    margin-bottom: 1.2rem;
}
.jami-hero h1, .jami-hero p { color: white !important; margin: 0; }
.jami-hero p { margin-top: 8px; opacity: 0.96; font-size: 1rem; line-height: 1.6; }
.jami-card {
    background: #fffdf9;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 20px;
    margin-bottom: 1rem;
}
.jami-card h3 { margin-top: 0; margin-bottom: 8px; }
.jami-muted { color: var(--muted) !important; }
.jami-pill {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    background: rgba(212,160,23,0.12);
    color: #8b5e34;
    margin-right: 6px;
    margin-bottom: 6px;
}
@media (max-width: 900px) {
    .block-container { padding-top: 0.75rem; padding-left: 0.9rem; padding-right: 0.9rem; }
    .jami-hero { padding: 20px; border-radius: 18px; }
    .jami-card { padding: 16px; border-radius: 16px; }
    .stButton > button { width: 100%; }
}

/* BEGIN SIDEBAR ACCESS THEME */

/* Teacher sign-in and Request Teacher Access cards */
section[data-testid="stSidebar"] details,
section[data-testid="stSidebar"] div[data-testid="stExpander"] details {
    background: linear-gradient(
        145deg,
        rgba(91, 57, 31, 0.96),
        rgba(55, 32, 18, 0.98)
    ) !important;
    border: 1px solid rgba(212, 160, 23, 0.45) !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.18) !important;
    overflow: hidden !important;
}

/* Expander heading area */
section[data-testid="stSidebar"] details > summary,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
    background: linear-gradient(
        90deg,
        rgba(92, 58, 32, 0.96),
        rgba(70, 43, 24, 0.96)
    ) !important;
    color: #fff2dc !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
}

/* Remove white background from expander body */
section[data-testid="stSidebar"] details > div,
section[data-testid="stSidebar"] div[data-testid="stExpanderDetails"] {
    background: transparent !important;
}

/* Teacher form labels */
section[data-testid="stSidebar"] details label,
section[data-testid="stSidebar"] details p,
section[data-testid="stSidebar"] details span {
    color: #f8e7cd !important;
}

/* Input boxes: warm cream rather than bright white */
section[data-testid="stSidebar"] details input,
section[data-testid="stSidebar"] details textarea {
    background: #f5ead8 !important;
    color: #2b1d14 !important;
    -webkit-text-fill-color: #2b1d14 !important;
    border: 1px solid #d4a017 !important;
    border-radius: 12px !important;
}

/* Input placeholders */
section[data-testid="stSidebar"] details input::placeholder,
section[data-testid="stSidebar"] details textarea::placeholder {
    color: #796552 !important;
    opacity: 1 !important;
}

/* Gold sign-in/request buttons */
section[data-testid="stSidebar"] details .stButton > button {
    background: linear-gradient(
        90deg,
        #9b672f 0%,
        #d4a017 100%
    ) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 220, 130, 0.30) !important;
    box-shadow: 0 6px 16px rgba(212, 160, 23, 0.20) !important;
}

/* Keep sidebar radio area consistent */
section[data-testid="stSidebar"] [data-testid="stRadio"] {
    background: transparent !important;
}

/* END SIDEBAR ACCESS THEME */


/* BEGIN TEACHER ACTIVATION THEME */

/* Teacher activation form container */
section[data-testid="stSidebar"] form {
    background: linear-gradient(
        145deg,
        rgba(91, 57, 31, 0.96),
        rgba(55, 32, 18, 0.98)
    ) !important;
    border: 1px solid rgba(212, 160, 23, 0.40) !important;
    border-radius: 16px !important;
    padding: 16px !important;
}

/* Password input outer containers */
section[data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {
    background: #efe1ca !important;
    border-radius: 12px !important;
}

/* Actual password inputs */
section[data-testid="stSidebar"] [data-testid="stTextInput"] input {
    background: #efe1ca !important;
    color: #2b1a10 !important;
    -webkit-text-fill-color: #2b1a10 !important;
    border: 1px solid #d4a017 !important;
    border-radius: 12px !important;
}

/* Password field labels */
section[data-testid="stSidebar"] [data-testid="stTextInput"] label,
section[data-testid="stSidebar"] [data-testid="stTextInput"] label p {
    color: #f8e7cd !important;
    font-weight: 600 !important;
}

/* Password reveal icon */
section[data-testid="stSidebar"] [data-testid="stTextInput"] button {
    color: #6d4b27 !important;
    background: transparent !important;
}

/* Activate Teacher Account button */
section[data-testid="stSidebar"] form .stButton > button,
section[data-testid="stSidebar"] form button[kind="secondaryFormSubmit"] {
    background: linear-gradient(
        90deg,
        #9b672f 0%,
        #d4a017 100%
    ) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 220, 130, 0.35) !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    min-height: 46px !important;
}

/* Error box */
section[data-testid="stSidebar"] [data-testid="stAlert"] {
    border-radius: 14px !important;
}

/* END TEACHER ACTIVATION THEME */

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="jami-hero">
    <h1>🇫🇷 French Reading Coach</h1>
    <p>
        <strong>Public Beta — Free to use.</strong> Practice French pronunciation, guided reading,
        and grammar immediately. No student account or payment is required.
    </p>
</div>
""", unsafe_allow_html=True)

_research_on, _research_status_message = research_status()
if _research_on:
    st.success("🔬 Optional research participation is available. Learning access does not depend on participating.")
else:
    st.info("🆓 Free public beta: guest learning is open. Research data collection is currently OFF unless separately activated under an approved study.")

render_auth_sidebar()

def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div style="margin: 0.4rem 0 1rem 0;">
            <h2 style="margin-bottom: 0.2rem;">{title}</h2>
            <p class="jami-muted" style="margin-top: 0;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="jami-card">
            <h3>{title}</h3>
            <p class="jami-muted">{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )



def build_pronunciation_targets(text: str, lesson_data=None):
    """
    Combine automatic connected-speech detection with the curated
    liaison_targets defined in teacher_texts.py.
    """
    automatic = detect_liaison_candidates(text) or []
    merged = {}

    # Automatic targets
    for item in automatic:
        point = dict(item)
        phrase = str(point.get("phrase", "") or "").strip()

        if not phrase:
            continue

        focus = point.get("focus_sound", "linked boundary")

        point["explanation"] = (
            "In connected French speech, these words belong together "
            "without an unnecessary pause. The important phonetic "
            f"connection at this boundary is {focus}."
        )

        merged[phrase.lower()] = point

    # Teacher-curated targets
    if lesson_data:
        for phrase in lesson_data.get("liaison_targets", []) or []:
            phrase = str(phrase).strip()

            if not phrase:
                continue

            key = phrase.lower()

            if key in merged:
                merged[key]["explanation"] = (
                    merged[key].get("explanation", "")
                    + " This phrase is specifically selected in this lesson "
                      "as a pronunciation target."
                )
                merged[key]["curated"] = True
                continue

            ipa = phonetic_transcription(phrase)

            connected_ipa = (
                f"/{ipa}/"
                if ipa and ipa != "IPA unavailable"
                else "IPA unavailable"
            )

            merged[key] = {
                "phrase": phrase,
                "connected_ipa": connected_ipa,
                "focus_sound": "connected-speech boundary",
                "tip": (
                    f"Say '{phrase}' slowly first. Then repeat it naturally "
                    "without inserting a pause between the target words."
                ),
                "explanation": (
                    "This is a teacher-selected connected-speech target. "
                    "Practice the words as one rhythmic unit and pay attention "
                    "to how the final sound of the first word connects with "
                    "the beginning of the following word."
                ),
                "curated": True,
            }

    return list(merged.values())


def render_target_phonetic_transcription(text: str):
    """Display broad canonical IPA before the learner records."""
    if not text or not text.strip():
        return

    ipa = phonetic_transcription(text)

    st.markdown("### 🔤 Target phonetic transcription")

    if ipa and ipa != "IPA unavailable":
        st.code(f"/{ipa}/", language=None)
        st.caption(
            "Broad canonical French IPA for the target text. "
            "Use it as a pronunciation guide before recording."
        )
    else:
        st.warning("IPA transcription is temporarily unavailable.")


def play_tts_audio_safe(text: str, lang: str = "fr", key_prefix: str = "tts") -> None:
    if not text or not text.strip():
        st.error("No text available for audio.")
        return

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
            temp_path = tmp_mp3.name

        tts = gTTS(text=text, lang=lang)
        tts.save(temp_path)

        with open(temp_path, "rb") as audio_file:
            audio_bytes = audio_file.read()

        st.audio(audio_bytes, format="audio/mpeg")
        st.download_button(
            "Download audio",
            data=audio_bytes,
            file_name=f"{key_prefix}.mp3",
            mime="audio/mpeg",
            key=f"{key_prefix}_download",
        )

    except Exception as e:
        st.error(f"Could not generate audio: {e}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


if "reference_text" not in st.session_state:
    st.session_state.reference_text = DEFAULT_TEXT
if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "teacher_mode" not in st.session_state:
    st.session_state.teacher_mode = False
if "teacher_name" not in st.session_state:
    st.session_state.teacher_name = ""
if "grammar_index" not in st.session_state:
    st.session_state.grammar_index = 0
if "grammar_score" not in st.session_state:
    st.session_state.grammar_score = 0
if "grammar_xp" not in st.session_state:
    st.session_state.grammar_xp = 0
if "active_grammar_lesson_id" not in st.session_state:
    st.session_state.active_grammar_lesson_id = None
if "guided_section_index" not in st.session_state:
    st.session_state.guided_section_index = 0
if "active_guided_task_id" not in st.session_state:
    st.session_state.active_guided_task_id = None
if "latest_created_task_id" not in st.session_state:
    st.session_state.latest_created_task_id = None

ensure_all_seeded()

st.sidebar.markdown("""
<div style="
    background: rgba(255, 233, 190, 0.10);
    border: 1px solid rgba(212,160,23,0.20);
    padding: 14px;
    border-radius: 14px;
    margin-bottom: 12px;
">
    <strong style="color:#f7e7ce;">French Reading Coach</strong><br>
    <span style="font-size: 13px; color:#f3dcc0;">
        Free public beta with pronunciation, guided reading, grammar, and optional teacher-supported progress.
    </span>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("Access")
mode = st.sidebar.radio("Open app as:", ["Student", "Teacher"], key="access_mode")

if mode == "Student":
    st.session_state.teacher_mode = False
    st.session_state.teacher_name = ""

    if st.session_state.student_id is None:
        st.sidebar.success("Guest access active")
        st.sidebar.caption(
            "Start learning immediately. A student profile is optional and is only needed to save progress, receive assignments, and appear in teacher tracking."
        )

        with st.sidebar.expander("Save progress with a student profile (optional)", expanded=False):
            st.subheader("Create or load profile")
            full_name = st.text_input("Full name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            level = st.selectbox("Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
            class_name = st.text_input("Class name")
            teacher_name_input = st.text_input("Teacher name")
            notes = st.text_area("Notes (optional)")

            if st.button("Create / Continue profile"):
                if not full_name.strip():
                    st.error("Full name is required to save a profile.")
                elif not email.strip():
                    st.error(
                        "Email is required only when you choose to save progress. "
                        "Guest learning remains available without an email."
                    )
                else:
                    student, msg = create_or_get_student(
                        full_name=full_name,
                        email=email,
                        phone=phone,
                        level=level,
                        class_name=class_name,
                        teacher_name=teacher_name_input,
                        notes=notes,
                    )
                    if student:
                        st.session_state.student_id = student["id"]
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            st.markdown("---")
            st.subheader("Find existing profile")
            lookup_name = st.text_input("Name to find", key="lookup_name")
            lookup_email = st.text_input("Email to find", key="lookup_email")

            if st.button("Find my profile"):
                if not lookup_name.strip() or not lookup_email.strip():
                    st.error(
                        "Enter both the full name and email used to create the profile."
                    )
                else:
                    student = find_student_by_email_or_name(
                        lookup_name,
                        lookup_email,
                    )
                    if student:
                        st.session_state.student_id = student["id"]
                        st.success("Profile found.")
                        st.rerun()
                    else:
                        st.error(
                            "No profile matched both that full name and email."
                        )
    else:
        current_student = get_student(st.session_state.student_id)
        if current_student:
            st.sidebar.success(f"Student: {current_student.get('full_name', '')}")
            st.sidebar.write(f"Email: {current_student.get('email', '') or '—'}")
            st.sidebar.write(f"Level: {current_student.get('level', '') or '—'}")
            st.sidebar.write(f"Class: {current_student.get('class_name', '') or '—'}")
            if st.sidebar.button("Use guest access instead"):
                st.session_state.student_id = None
                st.rerun()
        else:
            st.session_state.student_id = None
            st.rerun()
else:
    st.session_state.teacher_mode = True

    current_user = get_current_user()

    if current_user is None:
        st.session_state.teacher_name = ""
        st.sidebar.info(
            "Teacher access requires administrator approval. Use ‘Teacher sign in’ above if you already have an approved account, or ‘Request Teacher Access’ to apply."
        )
    else:
        teacher_email = (getattr(current_user, "email", "") or "").strip().lower()
        teacher_profile = get_teacher_profile_by_email(teacher_email)

        if teacher_profile:
            approved_name = get_teacher_display_name(teacher_profile)
            st.session_state.teacher_name = approved_name
            st.sidebar.success(f"Teacher access granted: {approved_name}")
            role = (teacher_profile.get("role") or "teacher").strip().title()
            st.sidebar.caption(f"Role: {role}")
        else:
            st.session_state.teacher_name = ""
            access_record = get_teacher_access_record(teacher_email)
            if access_record:
                status = access_record.get("invite_status") or "pending/inactive"
                st.sidebar.warning(
                    f"Your teacher record is not active yet (status: {status}). An administrator must approve and activate it before dashboard access is granted."
                )
            else:
                st.sidebar.error(
                    "This signed-in email is not approved for teacher access. Submit a teacher-access request or contact the administrator."
                )

student_id = st.session_state.student_id
teacher_mode = st.session_state.teacher_mode
teacher_name = st.session_state.teacher_name

if teacher_mode and teacher_name:
    tab1, tab2, tab3, tab4, tab5, research_tab = st.tabs(
        ["🎤 Pronunciation", "🎮 Grammar Game", "📚 Guided Reading", "📊 Progress", "👩‍🏫 Teacher Dashboard", "🔬 Research Beta"]
    )
else:
    tab1, tab2, tab3, tab4, research_tab = st.tabs(
        ["🎤 Pronunciation", "🎮 Grammar Game", "📚 Guided Reading", "📊 Progress", "🔬 Research Beta"]
    )
    if student_id is None:
        st.info("Guest mode is active. You can use the learning tools now; create a student profile only if you want progress saved and teacher assignments tracked.")


with tab1:
    section_header("🎤 Pronunciation Practice", "Upload text, listen, record, and receive structured feedback.")
    current_lesson_id = None
    selected_text_data = None
    input_mode = st.radio("Choose text source:", ["My Text", "Teacher Texts"], key="input_mode")

    if input_mode == "My Text":
        uploaded_file = st.file_uploader(
            "Upload a PDF, Word, or text file",
            type=["pdf", "docx", "txt"],
            key="text_upload",
        )

        if uploaded_file is not None:
            file_name = uploaded_file.name.lower()
            try:
                if file_name.endswith(".pdf"):
                    extracted_text = extract_text_from_pdf(uploaded_file)
                elif file_name.endswith(".docx"):
                    extracted_text = extract_text_from_docx(uploaded_file)
                elif file_name.endswith(".txt"):
                    extracted_text = extract_text_from_txt(uploaded_file)
                else:
                    extracted_text = ""

                if extracted_text:
                    st.session_state.reference_text = extracted_text
                    st.success("File uploaded and text extracted successfully.")
                else:
                    st.warning("The file was uploaded, but no readable text was found.")
            except Exception as e:
                st.error(f"Could not read file: {e}")

        reference_text = st.text_area(
            "Type or paste your French text here:",
            value=st.session_state.reference_text,
            height=220,
            key="reference_text_area_my",
        )
        st.session_state.reference_text = reference_text

    else:
        selected_level = st.selectbox("Choose CEFR level:", ["A1", "A2", "B1", "B2", "C1", "C2"], key="teacher_level")
        filtered_texts = [t for t in TEACHER_TEXTS if t["level"] == selected_level]
        lesson_options = {make_lesson_label(t): t for t in filtered_texts}

        selected_label = st.selectbox("Choose a lesson:", list(lesson_options.keys()), key="teacher_lesson")
        selected_text_data = lesson_options[selected_label]
        current_lesson_id = get_lesson_id_for_text(selected_text_data)

        render_lesson_card(selected_text_data)

        reference_text = st.text_area(
            "Teacher text:",
            value=selected_text_data["text"],
            height=220,
            key="reference_text_area_teacher",
        )
        st.session_state.reference_text = reference_text


    # Full IPA before recording
    render_target_phonetic_transcription(reference_text)

    # Connected-speech / liaison targets
    pronunciation_targets = build_pronunciation_targets(
        reference_text,
        selected_text_data,
    )

    if pronunciation_targets:
        render_pronunciation_focus(
            text=reference_text,
            liaison_points=pronunciation_targets,
            context="preview",
            current_user_id=student_id,
            current_lesson_id=current_lesson_id,
            phrase_history_key="pronunciation_phrase_history",
            max_phrase_attempts=MAX_PHRASE_ATTEMPTS,
            enable_phrase_recording=False,
        )
    else:
        st.caption(
            "No specific liaison or connected-speech target was identified "
            "for this text."
        )

    if st.button("🔊 Listen to pronunciation", key="listen_main"):
        if not reference_text.strip():
            st.error("Please type, paste, upload, or select a French text first.")
        else:
            play_tts_audio_safe(
                text=reference_text,
                lang="fr",
                key_prefix="main_pronunciation",
            )
            st.caption("On iPhone, if audio does not autoplay, tap play or use the download button.")

    st.markdown("---")
    audio_value = st.audio_input("🎤 Record your pronunciation", key="main_audio_input")
    uploaded_audio = st.file_uploader(
        "Or upload audio (wav, mp3, m4a)",
        type=["wav", "mp3", "m4a"],
        key="uploaded_audio_fallback",
    )

    def process_audio_bytes(audio_source, analyze_key: str) -> None:
        if not reference_text.strip():
            st.error("Please type, paste, upload, or select a French text first.")
            return

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                tmp_wav.write(audio_source.read())
                wav_path = tmp_wav.name

            transcript = transcribe_audio_file(wav_path)

            # Full IPA + acoustic/prosodic analysis
            target_full_ipa = phonetic_transcription(reference_text)
            recognized_full_ipa = phonetic_transcription(transcript)
            acoustic = analyze_speech_acoustics(
                wav_path,
                transcript=transcript,
            )

            score = pronunciation_score(reference_text, transcript)
            feedback = word_feedback(reference_text, transcript)
            attempt_issue = detect_attempt_issue(reference_text, transcript, feedback)
            liaison_points = build_pronunciation_targets(
                reference_text,
                selected_text_data,
            )
            coaching_message = generate_coaching_message(score, feedback, liaison_points)

            attempt = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "reference_text": reference_text,
                "recognized_text": transcript,
                "score": score,
                "feedback": feedback,
                "mode": input_mode,
                "coaching_message": coaching_message,
            }

            save_attempt_to_db(student_id, current_lesson_id, attempt)
            log_research_event(
                "pronunciation_analysis",
                "pronunciation",
                {
                    "score": float(score),
                    "input_mode": input_mode,
                    "lesson_id": str(current_lesson_id) if current_lesson_id else None,
                    "reference_word_count": len(reference_text.split()),
                    "recognized_word_count": len((transcript or "").split()),
                    "feedback_item_count": len(feedback or []),
                },
            )

            st.subheader("Results")
            st.write(f"**Recognized text:** {transcript}")
            st.write(f"**Pronunciation score:** {score}/100")
            st.warning(attempt_issue)
            render_coaching_message(coaching_message)

            if liaison_points:
                render_pronunciation_focus(
                    text=reference_text,
                    liaison_points=liaison_points,
                    context=analyze_key,
                    current_user_id=student_id,
                    current_lesson_id=current_lesson_id,
                    phrase_history_key="pronunciation_phrase_history",
                    max_phrase_attempts=MAX_PHRASE_ATTEMPTS,
                    enable_phrase_recording=True,
                )

            st.markdown("### Word-by-word feedback")
            st.markdown(render_colored_feedback_with_ipa(feedback), unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### Complete Speech & Phonetic Analysis")

            st.markdown("#### Full phonetic transcription (IPA)")
            st.write("**Target text:**")
            st.code(target_full_ipa, language=None)

            st.write("**Recognized speech:**")
            st.code(recognized_full_ipa, language=None)

            st.caption(
                "IPA is a broad canonical transcription of the target and "
                "recognized French text. It complements, rather than replaces, "
                "manual narrow phonetic transcription."
            )

            if acoustic.get("analysis_error"):
                st.warning(
                    "Some acoustic measurements could not be calculated: "
                    + str(acoustic.get("analysis_error"))
                )
            else:
                st.markdown("#### Acoustic & prosodic measures")

                c1, c2, c3, c4 = st.columns(4)

                c1.metric(
                    "Duration",
                    f"{acoustic['duration_s']:.2f} s"
                    if acoustic.get("duration_s") is not None
                    else "—",
                )

                c2.metric(
                    "Mean F0",
                    f"{acoustic['f0_mean_hz']:.1f} Hz"
                    if acoustic.get("f0_mean_hz") is not None
                    else "—",
                )

                c3.metric(
                    "F0 range",
                    f"{acoustic['f0_range_hz']:.1f} Hz"
                    if acoustic.get("f0_range_hz") is not None
                    else "—",
                )

                c4.metric(
                    "Mean intensity",
                    f"{acoustic['intensity_mean_db']:.1f} dB"
                    if acoustic.get("intensity_mean_db") is not None
                    else "—",
                )

                c5, c6, c7, c8 = st.columns(4)

                c5.metric(
                    "F0 minimum",
                    f"{acoustic['f0_min_hz']:.1f} Hz"
                    if acoustic.get("f0_min_hz") is not None
                    else "—",
                )

                c6.metric(
                    "F0 maximum",
                    f"{acoustic['f0_max_hz']:.1f} Hz"
                    if acoustic.get("f0_max_hz") is not None
                    else "—",
                )

                c7.metric(
                    "Estimated speech rate",
                    f"{acoustic['speech_rate_syll_s']:.2f} syll/s"
                    if acoustic.get("speech_rate_syll_s") is not None
                    else "—",
                )

                c8.metric(
                    "Final pitch",
                    acoustic.get("final_pitch_direction", "—"),
                )

                c9, c10, c11, c12 = st.columns(4)

                c9.metric(
                    "Median F1",
                    f"{acoustic['f1_median_hz']:.0f} Hz"
                    if acoustic.get("f1_median_hz") is not None
                    else "—",
                )

                c10.metric(
                    "Median F2",
                    f"{acoustic['f2_median_hz']:.0f} Hz"
                    if acoustic.get("f2_median_hz") is not None
                    else "—",
                )

                c11.metric(
                    "Final F0",
                    f"{acoustic['final_f0_hz']:.1f} Hz"
                    if acoustic.get("final_f0_hz") is not None
                    else "—",
                )

                c12.metric(
                    "Final F0 change",
                    f"{acoustic['final_pitch_change_hz']:+.1f} Hz"
                    if acoustic.get("final_pitch_change_hz") is not None
                    else "—",
                )

                with st.expander("See detailed speech measurements"):
                    st.write(
                        f"**Recognized words:** "
                        f"{acoustic.get('word_count', 0)}"
                    )
                    st.write(
                        f"**Estimated syllables:** "
                        f"{acoustic.get('syllable_count_est', 0)}"
                    )

                    slope = acoustic.get(
                        "final_pitch_slope_hz_s"
                    )

                    st.write(
                        "**Final pitch slope:** "
                        + (
                            f"{slope:+.2f} Hz/s"
                            if slope is not None
                            else "—"
                        )
                    )

                    st.caption(
                        "F1/F2 values are global exploratory summaries across "
                        "the utterance; vowel-specific formant analysis requires "
                        "segment-level alignment."
                    )

        except Exception as e:
            st.error(f"Analysis failed: {e}")

    if audio_value is not None:
        st.audio(audio_value, format="audio/wav")
        if st.button("📊 Analyze pronunciation", key="analyze_live_audio"):
            process_audio_bytes(audio_value, "results_live")

    if uploaded_audio is not None:
        st.audio(uploaded_audio)
        if st.button("📊 Analyze uploaded audio", key="analyze_uploaded_audio"):
            process_audio_bytes(uploaded_audio, "results_uploaded")


with tab2:
    section_header("🎮 Grammar Game", "Build accuracy, earn XP, and strengthen your command of French.")
    grammar_level = st.selectbox("Choose grammar level:", ["A1", "A2", "B1", "B2"], key="grammar_level")
    grammar_lessons = get_grammar_lessons(grammar_level)

    if grammar_lessons:
        lesson_map = {f"{row['title']} — {row['topic']}": row for row in grammar_lessons}
        selected_grammar_label = st.selectbox("Choose a grammar lesson:", list(lesson_map.keys()), key="grammar_lesson_select")
        selected_grammar_lesson = lesson_map[selected_grammar_label]
        grammar_lesson_id = selected_grammar_lesson["id"]

        if st.session_state.active_grammar_lesson_id != grammar_lesson_id:
            st.session_state.active_grammar_lesson_id = grammar_lesson_id
            grammar_summary = get_grammar_attempt_summary(student_id, grammar_lesson_id)
            st.session_state.grammar_index = grammar_summary["answered"]
            st.session_state.grammar_score = grammar_summary["correct"]
            st.session_state.grammar_xp = grammar_summary["xp"]

        st.markdown(f"### {selected_grammar_lesson['title']}")
        st.info(selected_grammar_lesson["explanation"])

        grammar_progress = get_grammar_progress(student_id, grammar_lesson_id)
        if grammar_progress:
            c1, c2, c3 = st.columns(3)
            c1.metric("XP", grammar_progress.get("total_xp", 0))
            c2.metric("Streak", grammar_progress.get("streak_count", 0))
            c3.metric("Mastery", grammar_progress.get("mastery_level", "Starter"))

        grammar_questions = get_grammar_questions(grammar_lesson_id)
        current_index = min(st.session_state.grammar_index, len(grammar_questions))
        st.progress(current_index / len(grammar_questions) if grammar_questions else 0)

        if grammar_questions and current_index < len(grammar_questions):
            q = grammar_questions[current_index]
            st.markdown(f"#### Question {current_index + 1} of {len(grammar_questions)}")
            st.write(q["prompt"])

            if q["question_type"] == "multiple_choice":
                user_answer = st.radio("Choose one:", q.get("options") or [], key=f"grammar_q_{q['id']}")
            else:
                user_answer = st.text_input("Your answer:", key=f"grammar_q_{q['id']}")

            if st.button("✅ Check answer", key=f"check_{q['id']}"):
                normalized_user = user_answer.strip().lower().replace("’", "'")
                normalized_correct = q["correct_answer"].strip().lower().replace("’", "'")
                is_correct = normalized_user == normalized_correct
                xp_earned = int(q.get("xp_value", 10)) if is_correct else 0

                save_grammar_attempt(
                    student_id=student_id,
                    lesson_id=grammar_lesson_id,
                    question_id=q["id"],
                    user_answer=user_answer,
                    is_correct=is_correct,
                    xp_earned=xp_earned,
                )
                update_grammar_progress(student_id, grammar_lesson_id)
                log_research_event(
                    "grammar_answer_checked",
                    "grammar",
                    {
                        "cefr_level": grammar_level,
                        "lesson_id": str(grammar_lesson_id),
                        "question_id": str(q["id"]),
                        "question_type": q.get("question_type"),
                        "is_correct": bool(is_correct),
                        "xp_earned": int(xp_earned),
                    },
                )

                if is_correct:
                    st.success(f"Correct! +{xp_earned} XP")
                else:
                    st.error("Not quite.")
                    st.write(f"**Correct answer:** {q['correct_answer']}")

                if q.get("explanation"):
                    st.info(q["explanation"])

            if st.button("➡ Next question", key=f"next_{q['id']}"):
                st.session_state.grammar_index = current_index + 1
                st.rerun()
        elif grammar_questions:
            st.success("🎉 Lesson complete!")


with tab3:
    section_header("📚 Guided Reading", "Read in short sections, answer questions, and build confidence.")
    assignments = get_assignments_for_student(student_id)

    if assignments:
        st.markdown("### My Assigned Readings")
        for assignment in assignments:
            task_info = assignment.get("guided_reading_tasks") or {}
            with st.expander(f"{task_info.get('title', 'Untitled')} | Status: {assignment.get('status', 'assigned')}"):
                st.write(f"**Assigned by:** {assignment.get('teacher_name', '')}")
                st.write(f"**Due date:** {assignment.get('due_date', '') or 'No due date'}")
                if assignment.get("notes"):
                    st.write(f"**Notes:** {assignment.get('notes')}")
                if task_info.get("instructions"):
                    st.write(f"**Instructions:** {task_info.get('instructions')}")
                if task_info.get("audio_url"):
                    st.audio(task_info["audio_url"])

    guided_level = st.selectbox("Choose reading level:", ["A1", "A2", "B1", "B2"], key="guided_level")
    tasks = get_guided_reading_tasks(guided_level)

    if tasks:
        task_map = {task["title"]: task for task in tasks}
        selected_task_title = st.selectbox("Choose a reading task:", list(task_map.keys()), key="guided_task_select")
        selected_task = task_map[selected_task_title]
        task_id = selected_task["id"]
        sections = get_guided_reading_sections(task_id)

        if st.session_state.active_guided_task_id != task_id:
            st.session_state.active_guided_task_id = task_id
            existing_attempt = get_latest_in_progress_guided_attempt(student_id, task_id)
            if existing_attempt:
                st.session_state.guided_section_index = get_guided_completed_section_count(existing_attempt["id"])
            else:
                st.session_state.guided_section_index = 0

        attempt = create_guided_reading_attempt(student_id, task_id)
        if attempt:
            mark_assignment_started(student_id, task_id)

        latest_status = get_guided_reading_attempt_status(student_id, task_id)

        st.markdown(f"### {selected_task['title']}")
        st.write(selected_task["full_text"])
        if selected_task.get("audio_url"):
            st.audio(selected_task["audio_url"])
        if selected_task.get("instructions"):
            st.info(selected_task["instructions"])

        if latest_status and latest_status.get("status") == "completed":
            c1, c2, c3 = st.columns(3)
            c1.metric("Pronunciation", latest_status.get("overall_pronunciation_score", 0))
            c2.metric("Comprehension", latest_status.get("comprehension_score", 0))
            c3.metric("Total Score", latest_status.get("total_score", 0))

        if sections:
            current_index = min(st.session_state.guided_section_index, len(sections))
            st.progress(current_index / len(sections))

            if current_index >= len(sections):
                st.success("🎉 Guided reading complete!")
                if attempt:
                    finalize_guided_reading_attempt(attempt["id"])
                    mark_assignment_completed(student_id, task_id)
            else:
                current_section = sections[current_index]
                st.markdown(f"#### Section {current_index + 1} of {len(sections)}")
                st.write(current_section["section_text"])

                if st.button("🔊 Listen to this section", key=f"listen_section_{current_section['id']}"):
                    play_tts_audio_safe(
                        text=current_section["section_text"],
                        lang="fr",
                        key_prefix=f"guided_section_{current_section['id']}",
                    )
                    st.caption("If iPhone playback is blocked, use the download button below the audio player.")

                # A retry nonce gives the student fresh controls when they
                # deliberately choose to try the same section again.
                retry_nonce_key = f"guided_retry_nonce_{current_section['id']}"
                retry_nonce = st.session_state.get(retry_nonce_key, 0)

                audio_key = f"guided_audio_{current_section['id']}_{retry_nonce}"
                comp_key = f"guided_comp_{current_section['id']}_{retry_nonce}"
                vocab_key = f"guided_vocab_{current_section['id']}_{retry_nonce}"
                feedback_state_key = f"guided_feedback_{current_section['id']}"

                section_audio = st.audio_input(
                    "🎤 Read this section aloud",
                    key=audio_key,
                )

                comprehension_response = st.text_input(
                    current_section["comprehension_question"],
                    key=comp_key,
                )

                vocab_response = st.text_input(
                    current_section["vocab_question"],
                    key=vocab_key,
                )

                if st.button(
                    "✅ Analyze & save feedback",
                    key=f"submit_section_{current_section['id']}_{retry_nonce}",
                ):
                    recognized_text = ""
                    pron_score = 0.0
                    coaching_message = "No audio submitted."
                    feedback = []

                    if section_audio is not None:
                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=".wav",
                        ) as tmp_wav:
                            tmp_wav.write(section_audio.read())
                            wav_path = tmp_wav.name

                        recognized_text = transcribe_audio_file(wav_path)

                        pron_score = pronunciation_score(
                            current_section["section_text"],
                            recognized_text,
                        )

                        feedback = word_feedback(
                            current_section["section_text"],
                            recognized_text,
                        )

                        coaching_message = generate_coaching_message(
                            pron_score,
                            feedback,
                            [],
                        )

                    comp_correct = (
                        normalize_simple(comprehension_response)
                        == normalize_simple(
                            current_section["comprehension_answer"]
                        )
                    )

                    vocab_correct = (
                        normalize_simple(vocab_response)
                        == normalize_simple(
                            current_section["vocab_answer"]
                        )
                    )

                    if student_id is not None and attempt:
                        saved_ok, saved_message = save_guided_section_attempt(
                            attempt_id=attempt["id"],
                            section_id=current_section["id"],
                            recognized_text=recognized_text,
                            pronunciation_score=pron_score,
                            comprehension_response=comprehension_response,
                            comprehension_correct=comp_correct,
                            vocab_response=vocab_response,
                            vocab_correct=vocab_correct,
                            coaching_message=coaching_message,
                        )

                        if not saved_ok:
                            st.error(
                                "This section could not be saved. "
                                + str(saved_message)
                            )
                            st.stop()

                    # Keep the feedback visible instead of immediately
                    # moving the student to the next section.
                    st.session_state[feedback_state_key] = {
                        "recognized_text": recognized_text,
                        "pronunciation_score": pron_score,
                        "coaching_message": coaching_message,
                        "word_feedback": feedback,
                        "audio_submitted": section_audio is not None,
                        "comprehension_response": comprehension_response,
                        "comprehension_correct": comp_correct,
                        "comprehension_answer": current_section[
                            "comprehension_answer"
                        ],
                        "vocab_response": vocab_response,
                        "vocab_correct": vocab_correct,
                        "vocab_answer": current_section["vocab_answer"],
                    }

                    log_research_event(
                        "guided_section_submitted",
                        "guided_reading",
                        {
                            "cefr_level": guided_level,
                            "task_id": str(task_id),
                            "section_id": str(current_section["id"]),
                            "section_order": int(
                                current_section.get(
                                    "section_order",
                                    current_index + 1,
                                )
                            ),
                            "pronunciation_score": float(pron_score),
                            "audio_submitted": bool(
                                section_audio is not None
                            ),
                            "comprehension_correct": bool(comp_correct),
                            "vocabulary_correct": bool(vocab_correct),
                        },
                    )

                # -----------------------------------------------------
                # STUDENT FEEDBACK PANEL
                # -----------------------------------------------------
                section_feedback = st.session_state.get(feedback_state_key)

                if section_feedback:
                    st.markdown("---")
                    st.markdown("### 🧭 Your feedback")

                    st.markdown("#### 🎤 What the app heard")
                    recognized = (
                        section_feedback.get("recognized_text")
                        or "No speech was recognized."
                    )
                    st.write(recognized)

                    st.metric(
                        "Pronunciation score",
                        f"{section_feedback.get('pronunciation_score', 0):.1f}/100",
                    )

                    st.markdown("#### 💡 Pronunciation coaching")
                    render_coaching_message(
                        section_feedback.get(
                            "coaching_message",
                            "Keep practicing.",
                        )
                    )

                    if (
                        section_feedback.get("audio_submitted")
                        and section_feedback.get("word_feedback")
                    ):
                        st.markdown("#### 🔎 Word-by-word feedback")
                        st.markdown(
                            render_colored_feedback_with_ipa(
                                section_feedback["word_feedback"]
                            ),
                            unsafe_allow_html=True,
                        )

                    st.markdown("#### 🧠 Comprehension")

                    if section_feedback.get("comprehension_correct"):
                        st.success("✅ Correct!")
                    else:
                        st.error("❌ Not quite yet.")

                    st.write(
                        "**Your answer:** "
                        + (
                            section_feedback.get(
                                "comprehension_response"
                            )
                            or "No answer"
                        )
                    )

                    st.write(
                        "**Correct answer:** "
                        + str(
                            section_feedback.get(
                                "comprehension_answer",
                                "",
                            )
                        )
                    )

                    if not section_feedback.get("comprehension_correct"):
                        st.info(
                            "Compare your answer with the correct answer, "
                            "then reread the section and notice the information "
                            "that answers the question."
                        )

                    st.markdown("#### 🧩 Vocabulary")

                    if section_feedback.get("vocab_correct"):
                        st.success("✅ Correct!")
                    else:
                        st.error("❌ Not quite yet.")

                    st.write(
                        "**Your answer:** "
                        + (
                            section_feedback.get("vocab_response")
                            or "No answer"
                        )
                    )

                    st.write(
                        "**Correct answer:** "
                        + str(
                            section_feedback.get(
                                "vocab_answer",
                                "",
                            )
                        )
                    )

                    if not section_feedback.get("vocab_correct"):
                        st.info(
                            "Study the correct expression, say it aloud, "
                            "and try the section again."
                        )

                    st.markdown("#### 🎯 What should I do next?")

                    retry_col, continue_col = st.columns(2)

                    with retry_col:
                        if st.button(
                            "🔄 Try this section again",
                            key=f"retry_guided_{current_section['id']}_{retry_nonce}",
                            use_container_width=True,
                        ):
                            st.session_state[retry_nonce_key] = retry_nonce + 1
                            st.session_state.pop(
                                feedback_state_key,
                                None,
                            )
                            st.rerun()

                    with continue_col:
                        if st.button(
                            "➡️ Continue to next section",
                            key=f"continue_guided_{current_section['id']}_{retry_nonce}",
                            use_container_width=True,
                        ):
                            st.session_state.pop(
                                feedback_state_key,
                                None,
                            )
                            st.session_state.guided_section_index = (
                                current_index + 1
                            )
                            st.rerun()



with tab4:
    section_header("📊 My Progress", "Track your attempts, phrase practice, and overall development.")
    if student_id is None:
        st.info("You are using guest access. Practice is available, but progress is not saved. Open the optional student profile in the sidebar whenever you want saved tracking.")
    current_student = get_student(student_id)

    if current_student:
        st.markdown(
            f'''
            <div class="jami-card">
                <h3>Progress Dashboard</h3>
                <p class="jami-muted">
                    Student: <strong>{current_student.get('full_name', '')}</strong><br>
                    Email: {current_student.get('email', '—') or '—'}<br>
                    Class: {current_student.get('class_name', '—') or '—'}<br>
                    Teacher: {current_student.get('teacher_name', '—') or '—'}
                </p>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    # =====================================================
    # UNIFIED STUDENT ACTIVITY
    # =====================================================
    st.markdown("---")
    section_header(
        "🧭 All My Learning Activity",
        "Pronunciation, Guided Reading, grammar, phrase practice, and assignments in one place.",
    )

    student_activity = get_student_learning_activity(
        student_id
    )

    if student_activity:
        completed_activity = [
            row for row in student_activity
            if row.get("status") == "completed"
        ]

        scored_activity = [
            row for row in completed_activity
            if row.get("score") is not None
        ]

        activity_scores = [
            float(row["score"])
            for row in scored_activity
        ]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "All Activities",
            len(student_activity),
        )

        c2.metric(
            "Completed",
            len(completed_activity),
        )

        c3.metric(
            "In Progress / Assigned",
            len(student_activity)
            - len(completed_activity),
        )

        c4.metric(
            "Average Score",
            (
                f"{sum(activity_scores) / len(activity_scores):.1f}/100"
                if activity_scores
                else "—"
            ),
        )

        activity_types = sorted(
            {
                row.get("activity_type", "")
                for row in student_activity
                if row.get("activity_type")
            }
        )

        selected_activity_type = st.selectbox(
            "Filter my activity:",
            ["All"] + activity_types,
            key="student_activity_filter",
        )

        filtered_activity = (
            student_activity
            if selected_activity_type == "All"
            else [
                row for row in student_activity
                if row.get("activity_type")
                == selected_activity_type
            ]
        )

        activity_rows = []

        for row in filtered_activity:
            completed = (
                row.get("status") == "completed"
            )

            activity_rows.append({
                "Activity": row.get(
                    "activity_type",
                    "",
                ),
                "Title": row.get(
                    "activity_title",
                    "",
                ),
                "Status": row.get(
                    "status",
                    "",
                ),
                "Score": (
                    round(float(row["score"]), 1)
                    if completed
                    and row.get("score") is not None
                    else "—"
                ),
                "Pronunciation": (
                    round(
                        float(
                            row["pronunciation_score"]
                        ),
                        1,
                    )
                    if completed
                    and row.get(
                        "pronunciation_score"
                    ) is not None
                    else "—"
                ),
                "Comprehension": (
                    round(
                        float(
                            row["comprehension_score"]
                        ),
                        1,
                    )
                    if completed
                    and row.get(
                        "comprehension_score"
                    ) is not None
                    else "—"
                ),
                "Grammar": (
                    round(
                        float(
                            row["grammar_score"]
                        ),
                        1,
                    )
                    if completed
                    and row.get(
                        "grammar_score"
                    ) is not None
                    else "—"
                ),
                "XP": (
                    row.get("xp")
                    if row.get("xp") is not None
                    else "—"
                ),
                "Date": row.get("date", ""),
            })

        st.dataframe(
            activity_rows,
            use_container_width=True,
        )

    elif student_id is not None:
        st.info(
            "No saved learning activity has been recorded yet."
        )

    # =====================================================
    # GUIDED READING PROGRESS & FEEDBACK
    # =====================================================
    st.markdown("---")
    section_header(
        "📚 Guided Reading Progress & Feedback",
        "Review your Guided Reading attempts, section scores, answers, and coaching.",
    )

    student_guided_attempts = []

    if student_id is not None:
        try:
            guided_overview = get_guided_reading_attempt_overview()

            student_guided_attempts = [
                attempt
                for attempt in guided_overview
                if str(attempt.get("student_id")) == str(student_id)
            ]
        except Exception:
            student_guided_attempts = []

    if student_guided_attempts:
        for attempt_number, attempt in enumerate(
            student_guided_attempts,
            start=1,
        ):
            task_info = attempt.get("guided_reading_tasks") or {}
            task_title = task_info.get("title") or "Guided Reading"

            status = attempt.get("status") or "in_progress"

            status_label = (
                "✅ Completed"
                if status == "completed"
                else "⏳ In Progress"
            )

            attempt_details = get_guided_reading_attempt_details(
                attempt["id"]
            )

            try:
                total_sections = len(
                    get_guided_reading_sections(
                        attempt.get("task_id")
                    )
                )
            except Exception:
                total_sections = 0

            completed_sections = len(attempt_details)

            expander_title = (
                f"{task_title} — {status_label} "
                f"— {completed_sections}/{total_sections or '?'} sections"
            )

            with st.expander(
                expander_title,
                expanded=(
                    attempt_number == 1
                    and status != "completed"
                ),
            ):
                p1, p2, p3, p4 = st.columns(4)

                p1.metric(
                    "Sections",
                    (
                        f"{completed_sections}/{total_sections}"
                        if total_sections
                        else str(completed_sections)
                    ),
                )

                p2.metric(
                    "Pronunciation",
                    (
                        f"{float(attempt.get('overall_pronunciation_score')):.1f}/100"
                        if (
                            status == "completed"
                            and attempt.get(
                                "overall_pronunciation_score"
                            ) is not None
                        )
                        else "—"
                    ),
                )

                p3.metric(
                    "Comprehension",
                    (
                        f"{float(attempt.get('comprehension_score')):.1f}/100"
                        if (
                            status == "completed"
                            and attempt.get(
                                "comprehension_score"
                            ) is not None
                        )
                        else "—"
                    ),
                )

                p4.metric(
                    "Total Score",
                    (
                        f"{float(attempt.get('total_score')):.1f}/100"
                        if (
                            status == "completed"
                            and attempt.get("total_score") is not None
                        )
                        else "—"
                    ),
                )

                if status != "completed":
                    st.info(
                        "This reading is still in progress. "
                        "Your section-level work below is already saved. "
                        "Overall scores appear after all sections are completed."
                    )

                if attempt_details:
                    st.markdown("#### Section-by-section learning record")

                    for detail in attempt_details:
                        section = (
                            detail.get("guided_reading_sections")
                            or {}
                        )

                        section_order = section.get(
                            "section_order",
                            "?",
                        )

                        section_text = section.get(
                            "section_text",
                            "",
                        )

                        pron_score = detail.get(
                            "pronunciation_score"
                        )

                        section_label = (
                            f"Section {section_order}"
                            + (
                                f" — Pronunciation: "
                                f"{float(pron_score):.1f}/100"
                                if pron_score is not None
                                else ""
                            )
                        )

                        with st.expander(section_label):
                            if section_text:
                                st.write(
                                    f"**Target text:** {section_text}"
                                )

                            st.write(
                                "**What the app recognized:** "
                                + (
                                    detail.get("recognized_text")
                                    or "No speech recognized."
                                )
                            )

                            if pron_score is not None:
                                st.metric(
                                    "Pronunciation score",
                                    f"{float(pron_score):.1f}/100",
                                )

                            coaching = detail.get(
                                "coaching_message"
                            )

                            if coaching:
                                st.markdown(
                                    "##### 💡 Pronunciation coaching"
                                )
                                render_coaching_message(
                                    coaching
                                )

                            st.markdown(
                                "##### 🧠 Comprehension"
                            )

                            comp_question = section.get(
                                "comprehension_question",
                                "",
                            )
                            comp_answer = section.get(
                                "comprehension_answer",
                                "",
                            )
                            comp_response = detail.get(
                                "comprehension_response"
                            ) or "No answer"
                            comp_correct = bool(
                                detail.get(
                                    "comprehension_correct"
                                )
                            )

                            if comp_question:
                                st.write(
                                    f"**Question:** {comp_question}"
                                )

                            st.write(
                                f"**Your answer:** {comp_response}"
                            )

                            if comp_correct:
                                st.success("✅ Correct")
                            else:
                                st.error("❌ Needs review")
                                if comp_answer:
                                    st.write(
                                        f"**Correct answer:** "
                                        f"{comp_answer}"
                                    )

                            st.markdown(
                                "##### 🧩 Vocabulary"
                            )

                            vocab_question = section.get(
                                "vocab_question",
                                "",
                            )
                            vocab_answer = section.get(
                                "vocab_answer",
                                "",
                            )
                            vocab_response = detail.get(
                                "vocab_response"
                            ) or "No answer"
                            vocab_correct = bool(
                                detail.get("vocab_correct")
                            )

                            if vocab_question:
                                st.write(
                                    f"**Question:** "
                                    f"{vocab_question}"
                                )

                            st.write(
                                f"**Your answer:** "
                                f"{vocab_response}"
                            )

                            if vocab_correct:
                                st.success("✅ Correct")
                            else:
                                st.error("❌ Needs review")
                                if vocab_answer:
                                    st.write(
                                        f"**Correct answer:** "
                                        f"{vocab_answer}"
                                    )
                else:
                    st.info(
                        "No completed sections have been saved "
                        "for this attempt yet."
                    )
    elif student_id is not None:
        st.info(
            "No Guided Reading activity has been recorded yet."
        )


    # =====================================================
    # LEGACY PERFORMANCE SUMMARY
    # Only show it if that older system actually has data.
    # Do NOT say 'No progress yet' when other activity exists.
    # =====================================================
    progress_rows = get_progress_rows(student_id)

    if progress_rows:
        st.markdown("---")
        section_header(
            "📊 Pronunciation Lesson Summary",
            "Summary of your standalone pronunciation lessons.",
        )

        total_attempts = sum(
            row["attempt_count"]
            for row in progress_rows
        )

        overall_best = max(
            float(row["best_score"])
            for row in progress_rows
        )

        overall_avg = round(
            sum(
                float(row["average_score"])
                for row in progress_rows
            )
            / len(progress_rows),
            2,
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Lessons Practiced",
            len(progress_rows),
        )

        c2.metric(
            "Total Attempts",
            total_attempts,
        )

        c3.metric(
            "Best Score",
            f"{overall_best:.1f}",
        )

        st.markdown(
            f"""
            <div class="jami-card">
                <h3>Performance Summary</h3>
                <p class="jami-muted">
                    Your average score across standalone
                    pronunciation lessons is
                    <strong>{overall_avg:.1f}</strong>.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


    # =====================================================
    # STANDALONE PRONUNCIATION HISTORY
    # =====================================================
    st.markdown("---")

    section_header(
        "📈 Standalone Pronunciation Practice",
        (
            "Recordings completed in the Pronunciation tab. "
            "Guided Reading pronunciation appears above."
        ),
    )

    attempt_history = get_attempt_history(
        student_id,
        limit=10,
    )

    if attempt_history:
        avg_score = (
            sum(
                float(a["score"])
                for a in attempt_history
            )
            / len(attempt_history)
        )

        st.metric(
            "Average Pronunciation Score",
            f"{avg_score:.1f}",
        )

        for i, attempt in enumerate(
            attempt_history,
            start=1,
        ):
            when = attempt.get("created_at", "")

            with st.expander(
                f"Attempt {i} — {when} — "
                f"Score: {attempt.get('score', 0)}/100"
            ):
                st.write(
                    f"**Mode:** "
                    f"{attempt.get('mode', 'Unknown')}"
                )

                st.write(
                    f"**Reference text:** "
                    f"{attempt.get('reference_text', '')}"
                )

                st.write(
                    f"**Recognized text:** "
                    f"{attempt.get('recognized_text', '')}"
                )

                feedback_data = attempt.get(
                    "feedback",
                    [],
                )

                if feedback_data:
                    st.markdown(
                        render_colored_feedback_with_ipa(
                            feedback_data
                        ),
                        unsafe_allow_html=True,
                    )
    else:
        st.info(
            "No standalone Pronunciation-tab attempts yet. "
            "Your Guided Reading pronunciation results "
            "are shown in Guided Reading Progress above."
        )


    # =====================================================
    # PHRASE PRACTICE HISTORY
    # =====================================================
    st.markdown("---")

    section_header(
        "🎯 Phrase Practice History",
        (
            "Focused phrase and connected-speech practice. "
            "This is separate from Guided Reading."
        ),
    )

    phrase_history = get_phrase_history(
        student_id,
        limit=10,
    )

    if phrase_history:
        for i, item in enumerate(
            phrase_history,
            start=1,
        ):
            when = item.get("created_at", "")

            with st.expander(
                f"Phrase Attempt {i} — {when} — "
                f"{item.get('phrase', '')}"
            ):
                st.write(
                    f"**Recognized phrase:** "
                    f"{item.get('recognized_phrase', '')}"
                )

                st.write(
                    f"**Phrase score:** "
                    f"{item.get('score', 0)}/100"
                )

                feedback_data = item.get(
                    "feedback",
                    [],
                )

                if feedback_data:
                    st.markdown(
                        render_colored_feedback_with_ipa(
                            feedback_data
                        ),
                        unsafe_allow_html=True,
                    )
    else:
        st.info(
            "No dedicated phrase-practice attempts yet."
        )


if teacher_mode and teacher_name:
    with tab5:
        section_header("👩‍🏫 Teacher Dashboard", "Assign tasks, monitor learners, and review performance with clarity.")

        st.markdown(
            f'''
            <div class="jami-card">
                <h3>Teacher Access</h3>
                <p class="jami-muted">
                    You are logged in as <strong>{teacher_name}</strong>.
                </p>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        students = get_all_students()
        tasks = get_guided_reading_tasks()

        c1, c2, c3 = st.columns(3)
        c1.metric("Students", len(students))
        c2.metric("Reading Tasks", len(tasks))
        c3.metric("Assignments", len(get_all_assignments_overview()))

        st.markdown("---")
        section_header(
            "🧭 All Student Learning Activity",
            "One view of pronunciation, Guided Reading, grammar, phrase practice, and assignments.",
        )

        all_activity = get_all_learning_activity()

        if all_activity:
            completed_activity = [
                row for row in all_activity
                if row.get("status") == "completed"
            ]

            scored_activity = [
                row for row in completed_activity
                if row.get("score") is not None
            ]

            teacher_scores = [
                float(row["score"])
                for row in scored_activity
            ]

            a1, a2, a3, a4 = st.columns(4)

            a1.metric(
                "Activity Records",
                len(all_activity),
            )

            a2.metric(
                "Completed",
                len(completed_activity),
            )

            a3.metric(
                "In Progress / Assigned",
                len(all_activity)
                - len(completed_activity),
            )

            a4.metric(
                "Average Score",
                (
                    f"{sum(teacher_scores) / len(teacher_scores):.1f}/100"
                    if teacher_scores
                    else "—"
                ),
            )

            student_options = sorted(
                {
                    row.get("student_name", "")
                    for row in all_activity
                    if row.get("student_name")
                }
            )

            class_options = sorted(
                {
                    row.get("class_name", "")
                    for row in all_activity
                    if row.get("class_name")
                }
            )

            type_options = sorted(
                {
                    row.get("activity_type", "")
                    for row in all_activity
                    if row.get("activity_type")
                }
            )

            f1, f2, f3, f4 = st.columns(4)

            student_filter = f1.selectbox(
                "Student",
                ["All"] + student_options,
                key="teacher_activity_student_filter",
            )

            class_filter = f2.selectbox(
                "Class",
                ["All"] + class_options,
                key="teacher_activity_class_filter",
            )

            type_filter = f3.selectbox(
                "Activity",
                ["All"] + type_options,
                key="teacher_activity_type_filter",
            )

            status_filter = f4.selectbox(
                "Status",
                [
                    "All",
                    "completed",
                    "in_progress",
                    "assigned",
                    "started",
                ],
                key="teacher_activity_status_filter",
            )

            filtered = all_activity

            if student_filter != "All":
                filtered = [
                    row for row in filtered
                    if row.get("student_name")
                    == student_filter
                ]

            if class_filter != "All":
                filtered = [
                    row for row in filtered
                    if row.get("class_name")
                    == class_filter
                ]

            if type_filter != "All":
                filtered = [
                    row for row in filtered
                    if row.get("activity_type")
                    == type_filter
                ]

            if status_filter != "All":
                filtered = [
                    row for row in filtered
                    if row.get("status")
                    == status_filter
                ]

            teacher_rows = []

            for row in filtered:
                completed = (
                    row.get("status") == "completed"
                )

                teacher_rows.append({
                    "Student": row.get(
                        "student_name",
                        "",
                    ),
                    "Email": row.get(
                        "email",
                        "",
                    ),
                    "Class": row.get(
                        "class_name",
                        "",
                    ),
                    "Level": row.get(
                        "level",
                        "",
                    ),
                    "Activity": row.get(
                        "activity_type",
                        "",
                    ),
                    "Title": row.get(
                        "activity_title",
                        "",
                    ),
                    "Status": row.get(
                        "status",
                        "",
                    ),
                    "Score": (
                        round(
                            float(row["score"]),
                            1,
                        )
                        if completed
                        and row.get("score")
                        is not None
                        else "—"
                    ),
                    "Pronunciation": (
                        round(
                            float(
                                row[
                                    "pronunciation_score"
                                ]
                            ),
                            1,
                        )
                        if completed
                        and row.get(
                            "pronunciation_score"
                        ) is not None
                        else "—"
                    ),
                    "Comprehension": (
                        round(
                            float(
                                row[
                                    "comprehension_score"
                                ]
                            ),
                            1,
                        )
                        if completed
                        and row.get(
                            "comprehension_score"
                        ) is not None
                        else "—"
                    ),
                    "Grammar": (
                        round(
                            float(
                                row[
                                    "grammar_score"
                                ]
                            ),
                            1,
                        )
                        if completed
                        and row.get(
                            "grammar_score"
                        ) is not None
                        else "—"
                    ),
                    "XP": (
                        row.get("xp")
                        if row.get("xp")
                        is not None
                        else "—"
                    ),
                    "Date": row.get(
                        "date",
                        "",
                    ),
                })

            st.dataframe(
                teacher_rows,
                use_container_width=True,
            )

        else:
            st.info(
                "No saved student learning activity yet."
            )

        st.markdown("---")
        section_header(
            "📌 Assign a Reading Task",
            "Choose an existing task, create one from teacher texts, or upload/paste a custom reading text with optional audio."
        )

        if students:
            student_map = {
                f"{s.get('full_name', '')} | {s.get('email', '') or 'no email'} | {s.get('class_name', '') or 'no class'}": s
                for s in students
            }

            selected_student_label = st.selectbox(
                "Choose student",
                list(student_map.keys()),
                key="assign_student_main",
            )
            selected_student_id = student_map[selected_student_label]["id"]

            assignment_mode = st.radio(
                "Task source",
                ["Existing Guided Task", "Teacher Text", "Custom Upload / Paste"],
                key="assignment_mode",
                horizontal=True,
            )

            due_date = st.date_input("Due date", key="assign_due_date")
            notes = st.text_area("Assignment notes", key="assign_notes")

            final_task_id = None

            if assignment_mode == "Existing Guided Task":
                if tasks:
                    task_map = {t["title"]: t for t in tasks}
                    selected_task_label = st.selectbox(
                        "Choose existing task",
                        list(task_map.keys()),
                        key="assign_existing_task",
                    )
                    final_task_id = task_map[selected_task_label]["id"]
                else:
                    st.info("No existing guided tasks found.")

            elif assignment_mode == "Teacher Text":
                teacher_level_for_task = st.selectbox(
                    "Choose CEFR level for teacher text",
                    ["A1", "A2", "B1", "B2", "C1", "C2"],
                    key="teacher_text_level_for_task",
                )

                filtered_teacher_texts = [t for t in TEACHER_TEXTS if t["level"] == teacher_level_for_task]
                teacher_text_map = {make_lesson_label(t): t for t in filtered_teacher_texts}

                if teacher_text_map:
                    selected_teacher_text_label = st.selectbox(
                        "Choose teacher text",
                        list(teacher_text_map.keys()),
                        key="assign_teacher_text",
                    )
                    selected_teacher_text = teacher_text_map[selected_teacher_text_label]

                    render_lesson_card(selected_teacher_text)

                    teacher_audio_file = st.file_uploader(
                        "Optional audio for this task",
                        type=["mp3", "wav", "m4a"],
                        key="teacher_text_audio_upload",
                    )

                    if st.button("Create task from teacher text", key="create_task_from_teacher_text_btn"):
                        audio_url = upload_teacher_audio(teacher_audio_file, teacher_name) if teacher_audio_file else None
                        new_task, msg = create_guided_task_from_teacher_text(
                            text_data=selected_teacher_text,
                            teacher_name=teacher_name,
                            audio_url=audio_url,
                        )
                        if new_task:
                            st.success(msg)
                            st.session_state.latest_created_task_id = new_task["id"]
                        else:
                            st.error(msg)

                    if st.session_state.latest_created_task_id:
                        final_task_id = st.session_state.latest_created_task_id
                else:
                    st.info("No teacher texts found for that level.")

            elif assignment_mode == "Custom Upload / Paste":
                custom_title = st.text_input("Task title", key="custom_task_title")
                custom_level = st.selectbox("Task level", ["A1", "A2", "B1", "B2", "C1", "C2"], key="custom_task_level")
                custom_theme = st.text_input("Theme", key="custom_task_theme")
                custom_instructions = st.text_area("Teacher instructions", key="custom_task_instructions")

                custom_text_file = st.file_uploader(
                    "Upload text file (pdf, docx, txt)",
                    type=["pdf", "docx", "txt"],
                    key="custom_task_text_upload",
                )

                uploaded_custom_text = ""
                if custom_text_file is not None:
                    file_name = custom_text_file.name.lower()
                    try:
                        if file_name.endswith(".pdf"):
                            uploaded_custom_text = extract_text_from_pdf(custom_text_file)
                        elif file_name.endswith(".docx"):
                            uploaded_custom_text = extract_text_from_docx(custom_text_file)
                        elif file_name.endswith(".txt"):
                            uploaded_custom_text = extract_text_from_txt(custom_text_file)
                    except Exception as e:
                        st.error(f"Could not extract text: {e}")

                custom_text = st.text_area(
                    "Paste or edit the task text",
                    value=uploaded_custom_text,
                    height=220,
                    key="custom_task_text_area",
                )

                custom_audio_file = st.file_uploader(
                    "Optional audio file",
                    type=["mp3", "wav", "m4a"],
                    key="custom_task_audio_upload",
                )

                if st.button("Create custom task", key="create_custom_task_btn"):
                    if not custom_title.strip():
                        st.error("Task title is required.")
                    elif not custom_text.strip():
                        st.error("Task text is required.")
                    else:
                        audio_url = upload_teacher_audio(custom_audio_file, teacher_name) if custom_audio_file else None
                        new_task, msg = create_guided_task(
                            title=custom_title,
                            cefr_level=custom_level,
                            theme=custom_theme,
                            full_text=custom_text,
                            teacher_name=teacher_name,
                            source_type="custom",
                            audio_url=audio_url,
                            instructions=custom_instructions,
                        )
                        if new_task:
                            st.success(msg)
                            st.session_state.latest_created_task_id = new_task["id"]
                        else:
                            st.error(msg)

                if st.session_state.latest_created_task_id:
                    final_task_id = st.session_state.latest_created_task_id

            if st.button("Assign selected task to student", key="assign_final_task_btn"):
                if not final_task_id:
                    st.error("Please choose or create a task first.")
                else:
                    ok, msg = assign_reading_task(
                        teacher_name=teacher_name,
                        student_id=selected_student_id,
                        task_id=final_task_id,
                        due_date=str(due_date) if due_date else None,
                        notes=notes,
                    )
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
        else:
            st.info("No students found yet.")

        st.markdown("---")
        section_header("📚 Assignment Overview", "A structured view of assigned readings, due dates, and completion status.")

        assignments = get_all_assignments_overview()
        if assignments:
            rows = []
            for assignment in assignments:
                task_info = assignment.get("guided_reading_tasks") or {}
                student_info = assignment.get("students") or {}
                rows.append(
                    {
                        "Student": student_info.get("full_name", ""),
                        "Email": student_info.get("email", ""),
                        "Class": student_info.get("class_name", ""),
                        "Assigned Teacher": assignment.get("teacher_name", ""),
                        "Task": task_info.get("title", ""),
                        "Level": task_info.get("cefr_level", ""),
                        "Source": task_info.get("source_type", ""),
                        "Status": assignment.get("status", ""),
                        "Due Date": assignment.get("due_date", ""),
                    }
                )
            st.dataframe(rows, use_container_width=True)
        else:
            card("No assignments yet", "Assignments will appear here once a reading task has been assigned to a student.")

        st.markdown("---")
        section_header("📊 Guided Reading Performance", "Monitor pronunciation, comprehension, and total reading performance.")

        attempts = get_guided_reading_attempt_overview()
        if attempts:
            summary_rows = []
            for attempt in attempts:
                task_info = attempt.get("guided_reading_tasks") or {}
                student_info = attempt.get("students") or {}
                summary_rows.append(
                    {
                        "Student": student_info.get("full_name", ""),
                        "Email": student_info.get("email", ""),
                        "Class": student_info.get("class_name", ""),
                        "Level": student_info.get("level", ""),
                        "Teacher": student_info.get("teacher_name", ""),
                        "Task": task_info.get("title", ""),
                        "Task Level": task_info.get("cefr_level", ""),
                        "Status": attempt.get("status", ""),
                        "Pronunciation": attempt.get("overall_pronunciation_score", 0) or 0,
                        "Comprehension": attempt.get("comprehension_score", 0) or 0,
                        "Total Score": attempt.get("total_score", 0) or 0,
                    }
                )
            st.dataframe(summary_rows, use_container_width=True)

            for i, attempt in enumerate(attempts, start=1):
                task_info = attempt.get("guided_reading_tasks") or {}
                student_info = attempt.get("students") or {}
                with st.expander(
                    f"{i}. {student_info.get('full_name', 'Unknown student')} | {task_info.get('title', 'Untitled task')} | {attempt.get('status', '')}"
                ):
                    st.write(f"**Student:** {student_info.get('full_name', '')}")
                    st.write(f"**Email:** {student_info.get('email', '')}")
                    st.write(f"**Class:** {student_info.get('class_name', '')}")
                    st.write(f"**Student level:** {student_info.get('level', '')}")
                    st.write(f"**Teacher:** {student_info.get('teacher_name', '')}")
                    st.write(f"**Task:** {task_info.get('title', '')}")
                    st.write(f"**Started:** {attempt.get('started_at', '')}")
                    st.write(f"**Completed:** {attempt.get('completed_at', '')}")

                    details = get_guided_reading_attempt_details(attempt["id"])
                    for section_row in details:
                        section_info = section_row.get("guided_reading_sections") or {}
                        with st.expander(f"Section {section_info.get('section_order', '')}", expanded=False):
                            st.write(f"**Section text:** {section_info.get('section_text', '')}")
                            st.write(f"**Recognized text:** {section_row.get('recognized_text', '')}")
                            st.write(f"**Pronunciation score:** {section_row.get('pronunciation_score', 0)}")
                            st.write(f"**Comprehension answer:** {section_row.get('comprehension_response', '')}")
                            st.write(f"**Expected comprehension:** {section_info.get('comprehension_answer', '')}")
                            st.write(f"**Vocabulary answer:** {section_row.get('vocab_response', '')}")
                            st.write(f"**Expected vocabulary:** {section_info.get('vocab_answer', '')}")
                            st.write(f"**Coaching message:** {section_row.get('coaching_message', '')}")
        else:
            card("No guided reading attempts yet", "Student performance data will appear here once guided reading activities are completed.")


with research_tab:
    section_header(
        "🔬 Public Research Beta",
        "Use the learning app freely. Research participation, when available, is separate, voluntary, and never required for access.",
    )

    enabled, status_message = research_status()
    if enabled:
        st.success(status_message)
    else:
        st.info(status_message)
        st.caption("The learning tools remain available normally while research collection is off.")

    with st.expander("Privacy and data-use summary", expanded=False):
        st.markdown(
            """
            **Guest learning:** You can use the learning activities without creating a student account.

            **Optional student profiles:** If you choose to create a profile, profile and progress information may be saved for your own progress and teacher-supported features. This is separate from research participation.

            **Research layer:** The research logger is inactive unless the study is explicitly enabled and you separately consent. The v1.0 research logger is designed to store an anonymous participant code and aggregate learning measures—not your name, email, IP address, raw microphone recording, pasted free text, or speech transcript.

            **Audio processing:** Audio you submit must be processed to provide pronunciation feedback. The research layer does not store the raw audio in this beta design.

            **Beta feedback:** Product feedback is stored separately from the research dataset and should be treated as operational feedback unless an approved protocol/consent permits research use.
            """
        )

    research_state = get_research_state()

    if enabled and not research_state:
        st.markdown("### Participate voluntarily")
        st.write("Joining the research pilot is optional. Declining does not change your access to the app.")
        st.markdown(f"**Study approval/reference:** {RESEARCH_APPROVAL_REFERENCE}")
        st.markdown(f"**Consent version:** {RESEARCH_CONSENT_VERSION}")
        with st.expander("Read the participant information / consent", expanded=True):
            st.markdown(RESEARCH_CONSENT_TEXT)

        age_ok = st.checkbox("I confirm that I am 18 years of age or older.", key="research_age_18")
        consent_ok = st.checkbox(
            "I have read the information above and voluntarily consent to participate in this research pilot.",
            key="research_consent_ok",
        )
        research_level = st.selectbox(
            "French proficiency (optional)",
            ["Prefer not to say", "Beginner / A1", "Elementary / A2", "Intermediate / B1", "Upper-intermediate / B2", "Advanced / C1", "Proficient / C2", "Not sure"],
            key="research_french_level",
        )
        language_background = st.selectbox(
            "French language background (optional)",
            ["Prefer not to say", "French is my first language", "French is an additional/second language", "I am currently learning French", "Other"],
            key="research_language_background",
        )
        if st.button("Join the voluntary research pilot", key="join_research_pilot"):
            ok, msg, state = enroll_participant(age_ok, consent_ok, research_level, language_background)
            if ok:
                st.success(msg)
                st.caption(f"Your anonymous participant code is {state['participant_code']}. No name or email is required for this research session.")
                st.rerun()
            else:
                st.error(msg)

    elif enabled and research_state:
        st.markdown("### Research participation active")
        st.success(f"Anonymous participant code: {research_state['participant_code']}")
        st.caption("Only the instrumented aggregate activity measures are logged for this consented browser session.")
        if st.button("Stop research collection for this session", key="leave_research_pilot"):
            leave_research_session()
            st.success("Research collection has stopped for this browser session. You may continue using the learning app.")
            st.rerun()

    st.markdown("---")
    st.markdown("### Help improve the public beta")
    st.caption("This feedback is operational product feedback and is stored separately from the research dataset.")
    feedback_rating = st.slider("Overall experience", 1, 5, 4, key="beta_feedback_rating")
    feedback_category = st.selectbox(
        "Feedback category",
        ["General", "Pronunciation", "Guided Reading", "Grammar", "Teacher Access", "Accessibility", "Bug / technical issue", "Suggestion"],
        key="beta_feedback_category",
    )
    feedback_message = st.text_area("What worked well, what was difficult, or what should we improve?", key="beta_feedback_message")
    if st.button("Submit beta feedback", key="submit_beta_feedback"):
        ok, msg = submit_beta_feedback(feedback_rating, feedback_category, feedback_message)
        if ok:
            st.success("Thank you. Your beta feedback was submitted.")
        else:
            st.error(msg)

    current_auth_user = get_current_user()
    current_auth_email = (getattr(current_auth_user, "email", "") or "").strip().lower() if current_auth_user else ""
    if teacher_mode and teacher_name and is_research_admin(current_auth_email):
        st.markdown("---")
        st.markdown("### 🔐 Research Admin")
        st.caption("Visible only to an approved signed-in research-admin email. Exports require the service-role key in server-side Streamlit secrets.")
        if st.button("Load research summary", key="load_research_admin_summary"):
            summary, msg = get_research_admin_summary()
            if summary is None:
                st.error(msg)
            else:
                st.session_state.research_admin_summary = summary

        summary = st.session_state.get("research_admin_summary")
        if isinstance(summary, dict):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Participants", len(summary.get("participants", [])))
            c2.metric("Sessions", len(summary.get("sessions", [])))
            c3.metric("Research Events", len(summary.get("events", [])))
            c4.metric("Beta Feedback", len(summary.get("feedback", [])))

            for label, key, filename in [
                ("Participants", "participants", "research_participants.csv"),
                ("Sessions", "sessions", "research_sessions.csv"),
                ("Events", "events", "research_events.csv"),
                ("Beta Feedback", "feedback", "beta_feedback.csv"),
            ]:
                csv_data = rows_to_csv(summary.get(key, []))
                st.download_button(
                    f"Download {label} CSV",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    disabled=not bool(csv_data),
                    key=f"download_{key}_csv",
                )
