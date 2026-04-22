import tempfile
from datetime import datetime

import streamlit as st
from gtts import gTTS

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
    assign_reading_task,
    get_assignments_for_student,
    get_all_assignments_overview,
    mark_assignment_started,
    mark_assignment_completed,
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
)
from ui_helpers import (
    make_lesson_label,
    render_lesson_card,
    render_coaching_message,
    render_colored_feedback_with_ipa,
    render_pronunciation_focus,
)

MAX_PHRASE_ATTEMPTS = 10
DEFAULT_TEXT = "Bonjour, comment allez-vous aujourd'hui ?"

st.set_page_config(page_title="JamiSpeak French", page_icon="🇫🇷", layout="wide")

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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="jami-hero">
    <h1>🇫🇷 JamiSpeak French</h1>
    <p>
        A modern French learning platform for pronunciation, guided reading,
        grammar mastery, and teacher-supported progress tracking.
    </p>
</div>
""", unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'''
        <div style="margin: 0.4rem 0 1rem 0;">
            <h2 style="margin-bottom: 0.2rem;">{title}</h2>
            <p class="jami-muted" style="margin-top: 0;">{subtitle}</p>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def card(title: str, body: str) -> None:
    st.markdown(
        f'''
        <div class="jami-card">
            <h3>{title}</h3>
            <p class="jami-muted">{body}</p>
        </div>
        ''',
        unsafe_allow_html=True,
    )


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

ensure_all_seeded()

st.sidebar.markdown("""
<div style="
    background: rgba(255, 233, 190, 0.10);
    border: 1px solid rgba(212,160,23,0.20);
    padding: 14px;
    border-radius: 14px;
    margin-bottom: 12px;
">
    <strong style="color:#f7e7ce;">JamiSpeak Portal</strong><br>
    <span style="font-size: 13px; color:#f3dcc0;">
        Elegant French learning with pronunciation, guided reading, grammar, and teacher monitoring.
    </span>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("Access")
mode = st.sidebar.radio("Open app as:", ["Student", "Teacher"], key="access_mode")

if mode == "Student":
    st.session_state.teacher_mode = False
    st.session_state.teacher_name = ""

    if st.session_state.student_id is None:
        st.sidebar.subheader("Student profile")
        full_name = st.sidebar.text_input("Full name")
        email = st.sidebar.text_input("Email")
        phone = st.sidebar.text_input("Phone")
        level = st.sidebar.selectbox("Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
        class_name = st.sidebar.text_input("Class name")
        teacher_name_input = st.sidebar.text_input("Teacher name")
        notes = st.sidebar.text_area("Notes (optional)")

        if st.sidebar.button("Continue / Create profile"):
            if not full_name.strip():
                st.sidebar.error("Full name is required.")
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
                    st.sidebar.success(msg)
                    st.rerun()
                else:
                    st.sidebar.error(msg)

        st.sidebar.markdown("---")
        st.sidebar.subheader("Find existing profile")
        lookup_name = st.sidebar.text_input("Name to find", key="lookup_name")
        lookup_email = st.sidebar.text_input("Email to find", key="lookup_email")

        if st.sidebar.button("Find my profile"):
            student = find_student_by_email_or_name(lookup_name, lookup_email)
            if student:
                st.session_state.student_id = student["id"]
                st.sidebar.success("Profile found.")
                st.rerun()
            else:
                st.sidebar.error("No matching profile found.")
    else:
        current_student = get_student(st.session_state.student_id)
        if current_student:
            st.sidebar.success(f"Student: {current_student.get('full_name', '')}")
            st.sidebar.write(f"Email: {current_student.get('email', '') or '—'}")
            st.sidebar.write(f"Level: {current_student.get('level', '') or '—'}")
            st.sidebar.write(f"Class: {current_student.get('class_name', '') or '—'}")
            if st.sidebar.button("Switch student"):
                st.session_state.student_id = None
                st.rerun()
        else:
            st.session_state.student_id = None
            st.rerun()
else:
    st.session_state.teacher_mode = True
    teacher_name_input = st.sidebar.text_input("Teacher name")
    if st.sidebar.button("Open teacher dashboard"):
        if is_teacher_name(teacher_name_input):
            st.session_state.teacher_name = teacher_name_input
            st.sidebar.success("Teacher access granted.")
            st.rerun()
        else:
            st.sidebar.error("Teacher name not authorized.")

student_id = st.session_state.student_id
teacher_mode = st.session_state.teacher_mode
teacher_name = st.session_state.teacher_name

if teacher_mode and teacher_name:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🎤 Pronunciation", "🎮 Grammar Game", "📚 Guided Reading", "📊 Progress", "👩‍🏫 Teacher Dashboard"]
    )
elif student_id:
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🎤 Pronunciation", "🎮 Grammar Game", "📚 Guided Reading", "📊 Progress"]
    )
else:
    st.info("Please create or load a student profile from the sidebar, or open teacher mode.")
    st.stop()

with tab1:
    section_header("🎤 Pronunciation Practice", "Upload text, listen, record, and receive structured feedback.")
    current_lesson_id = None
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

        auto_liaison_points = detect_liaison_candidates(reference_text)
        render_pronunciation_focus(
            text=reference_text,
            liaison_points=auto_liaison_points,
            context="preview",
            current_user_id=student_id,
            current_lesson_id=current_lesson_id,
            phrase_history_key="unused",
            max_phrase_attempts=MAX_PHRASE_ATTEMPTS,
            enable_phrase_recording=False,
        )

    if st.button("🔊 Listen to pronunciation", key="listen_main"):
        if not reference_text.strip():
            st.error("Please type, paste, upload, or select a French text first.")
        else:
            try:
                tts = gTTS(reference_text, lang="fr")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
                    tts.save(tmp_mp3.name)
                    with open(tmp_mp3.name, "rb") as f:
                        audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
            except Exception as e:
                st.error(f"Could not generate audio: {e}")

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
            score = pronunciation_score(reference_text, transcript)
            feedback = word_feedback(reference_text, transcript)
            attempt_issue = detect_attempt_issue(reference_text, transcript, feedback)
            liaison_points = detect_liaison_candidates(reference_text) if input_mode == "Teacher Texts" else []
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

            st.subheader("Results")
            st.write(f"**Recognized text:** {transcript}")
            st.write(f"**Pronunciation score:** {score}/100")
            st.warning(attempt_issue)
            render_coaching_message(coaching_message)

            if input_mode == "Teacher Texts":
                render_pronunciation_focus(
                    text=reference_text,
                    liaison_points=liaison_points,
                    context=analyze_key,
                    current_user_id=student_id,
                    current_lesson_id=current_lesson_id,
                    phrase_history_key="unused",
                    max_phrase_attempts=MAX_PHRASE_ATTEMPTS,
                    enable_phrase_recording=True,
                )

            st.markdown("### Word-by-word feedback")
            st.markdown(render_colored_feedback_with_ipa(feedback), unsafe_allow_html=True)

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
                    try:
                        tts = gTTS(current_section["section_text"], lang="fr")
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
                            tts.save(tmp_mp3.name)
                            with open(tmp_mp3.name, "rb") as f:
                                audio_bytes = f.read()
                        st.audio(audio_bytes, format="audio/mp3")
                    except Exception as e:
                        st.error(f"Could not generate section audio: {e}")

                section_audio = st.audio_input("🎤 Read this section aloud", key=f"guided_audio_{current_section['id']}")
                comprehension_response = st.text_input(current_section["comprehension_question"], key=f"guided_comp_{current_section['id']}")
                vocab_response = st.text_input(current_section["vocab_question"], key=f"guided_vocab_{current_section['id']}")

                if st.button("✅ Submit section", key=f"submit_section_{current_section['id']}"):
                    recognized_text = ""
                    pron_score = 0.0
                    coaching_message = "No audio submitted."

                    if section_audio is not None:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                            tmp_wav.write(section_audio.read())
                            wav_path = tmp_wav.name

                        recognized_text = transcribe_audio_file(wav_path)
                        pron_score = pronunciation_score(current_section["section_text"], recognized_text)
                        feedback = word_feedback(current_section["section_text"], recognized_text)
                        coaching_message = generate_coaching_message(pron_score, feedback, [])

                        st.write(f"**Recognized text:** {recognized_text}")
                        st.write(f"**Pronunciation score:** {pron_score}/100")
                        render_coaching_message(coaching_message)
                        st.markdown(render_colored_feedback_with_ipa(feedback), unsafe_allow_html=True)

                    comp_correct = normalize_simple(comprehension_response) == normalize_simple(current_section["comprehension_answer"])
                    vocab_correct = normalize_simple(vocab_response) == normalize_simple(current_section["vocab_answer"])

                    if attempt:
                        save_guided_section_attempt(
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

                if st.button("➡ Next section", key=f"next_guided_{current_section['id']}"):
                    st.session_state.guided_section_index = current_index + 1
                    st.rerun()

with tab4:
    section_header("📊 My Progress", "Track your attempts, phrase practice, and overall development.")
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

    progress_rows = get_progress_rows(student_id)

    if progress_rows:
        total_attempts = sum(row["attempt_count"] for row in progress_rows)
        overall_best = max(float(row["best_score"]) for row in progress_rows)
        overall_avg = round(sum(float(row["average_score"]) for row in progress_rows) / len(progress_rows), 2)

        c1, c2, c3 = st.columns(3)
        c1.metric("Lessons Practiced", len(progress_rows))
        c2.metric("Total Attempts", total_attempts)
        c3.metric("Best Score", f"{overall_best:.1f}")

        st.markdown(
            f'''
            <div class="jami-card">
                <h3>Performance Summary</h3>
                <p class="jami-muted">
                    Your average score across lessons is <strong>{overall_avg:.1f}</strong>.
                </p>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    else:
        card("No progress yet", "Complete a lesson or recording activity to begin tracking your learning journey.")

    st.markdown("---")
    section_header("📈 Pronunciation History", "Your most recent pronunciation attempts.")

    attempt_history = get_attempt_history(student_id, limit=10)
    if attempt_history:
        avg_score = sum(float(a["score"]) for a in attempt_history) / len(attempt_history)
        st.metric("Average Pronunciation Score", f"{avg_score:.1f}")

        for i, attempt in enumerate(attempt_history, start=1):
            when = attempt.get("created_at", "")
            with st.expander(f"Attempt {i} — {when} — Score: {attempt.get('score', 0)}/100"):
                st.write(f"**Mode:** {attempt.get('mode', 'Unknown')}")
                st.write(f"**Reference text:** {attempt.get('reference_text', '')}")
                st.write(f"**Recognized text:** {attempt.get('recognized_text', '')}")
                feedback_data = attempt.get("feedback", [])
                if feedback_data:
                    st.markdown(render_colored_feedback_with_ipa(feedback_data), unsafe_allow_html=True)
    else:
        card("No pronunciation attempts yet", "Record and analyze a reading to start building your pronunciation history.")

    st.markdown("---")
    section_header("🎯 Phrase History", "Focused practice on short phrases and connected speech.")

    phrase_history = get_phrase_history(student_id, limit=10)
    if phrase_history:
        for i, item in enumerate(phrase_history, start=1):
            when = item.get("created_at", "")
            with st.expander(f"Phrase Attempt {i} — {when} — {item.get('phrase', '')}"):
                st.write(f"**Recognized phrase:** {item.get('recognized_phrase', '')}")
                st.write(f"**Phrase score:** {item.get('score', 0)}/100")
                feedback_data = item.get("feedback", [])
                if feedback_data:
                    st.markdown(render_colored_feedback_with_ipa(feedback_data), unsafe_allow_html=True)
    else:
        card("No phrase attempts yet", "Practice highlighted phrases to build targeted phrase-level feedback history.")

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
        section_header("📌 Assign a Reading Task", "Select a student, choose a task, and attach notes or a due date.")

        if students and tasks:
            student_map = {
                f"{s.get('full_name', '')} | {s.get('email', '') or 'no email'} | {s.get('class_name', '') or 'no class'}": s
                for s in students
            }
            task_map = {t["title"]: t for t in tasks}

            selected_student_label = st.selectbox("Choose student", list(student_map.keys()), key="assign_student")
            selected_task_label = st.selectbox("Choose task", list(task_map.keys()), key="assign_task")
            due_date = st.date_input("Due date", key="assign_due_date")
            notes = st.text_area("Assignment notes", key="assign_notes")

            if st.button("Assign task", key="assign_task_btn"):
                ok, msg = assign_reading_task(
                    teacher_name=teacher_name,
                    student_id=student_map[selected_student_label]["id"],
                    task_id=task_map[selected_task_label]["id"],
                    due_date=str(due_date) if due_date else None,
                    notes=notes,
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

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
