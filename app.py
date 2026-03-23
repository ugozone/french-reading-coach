import streamlit as st
from teacher_texts import TEACHER_TEXTS

from auth import render_auth_sidebar, get_current_user_id
from db import (
    ensure_lessons_seeded,
    get_lesson_id_for_text,
    save_attempt_to_db,
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

st.set_page_config(page_title="French Reading Coach AI", page_icon="🇫🇷")

st.title("🇫🇷 French Reading Coach AI")
st.write(
    "Students can type, paste, or upload French text, or choose teacher texts by CEFR level, "
    "then listen, record themselves, and get pronunciation feedback."
)

MAX_ATTEMPTS = 5
MAX_PHRASE_ATTEMPTS = 10

# -----------------------------
# Session state
# -----------------------------
default_text = "Bonjour, comment allez-vous aujourd'hui ?"

if "reference_text" not in st.session_state:
    st.session_state.reference_text = default_text

if "attempt_history" not in st.session_state:
    st.session_state.attempt_history = []

if "phrase_history" not in st.session_state:
    st.session_state.phrase_history = []

# -----------------------------
# Auth
# -----------------------------
render_auth_sidebar()
current_user_id = get_current_user_id()

ensure_lessons_seeded()

# -----------------------------
# Input mode
# -----------------------------
input_mode = st.radio(
    "Choose text source:",
    ["My Text", "Teacher Texts"]
)

st.subheader("Choose how to add French text")

selected_text_data = None
auto_liaison_points = []
current_lesson_id = None

if input_mode == "My Text":
    uploaded_file = st.file_uploader(
        "Upload a PDF, Word, or text file",
        type=["pdf", "docx", "txt"]
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
        height=220
    )
    st.session_state.reference_text = reference_text

else:
    selected_level = st.selectbox(
        "Choose CEFR level:",
        ["A1", "A2", "B1", "B2", "C1", "C2"]
    )

    filtered_texts = [t for t in TEACHER_TEXTS if t["level"] == selected_level]
    lesson_options = {make_lesson_label(t): t for t in filtered_texts}

    selected_label = st.selectbox("Choose a lesson:", list(lesson_options.keys()))
    selected_text_data = lesson_options[selected_label]
    current_lesson_id = get_lesson_id_for_text(selected_text_data)

    render_lesson_card(selected_text_data)

    reference_text = st.text_area(
        "Teacher text:",
        value=selected_text_data["text"],
        height=220
    )
    st.session_state.reference_text = reference_text

    auto_liaison_points = detect_liaison_candidates(reference_text)
    render_pronunciation_focus(
        text=reference_text,
        liaison_points=auto_liaison_points,
        context="preview",
        current_user_id=current_user_id,
        current_lesson_id=current_lesson_id,
        phrase_history_key="phrase_history",
        max_phrase_attempts=MAX_PHRASE_ATTEMPTS,
        enable_phrase_recording=False,
    )

# -----------------------------
# Listen
# -----------------------------
from gtts import gTTS
import tempfile

if st.button("🔊 Listen to pronunciation"):
    if not reference_text.strip():
        st.error("Please type, paste, upload, or select a French text first.")
    else:
        try:
            tts = gTTS(reference_text, lang="fr")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
                tts.save(tmp_mp3.name)
                st.audio(tmp_mp3.name, format="audio/mp3")
        except Exception as e:
            st.error(f"Could not generate audio: {e}")

st.markdown("---")

# -----------------------------
# Analyze full sentence
# -----------------------------
st.info("Using local transcription temporarily while AWS Transcribe is unavailable.")

audio_value = st.audio_input("🎤 Record your pronunciation")

if audio_value is not None:
    st.audio(audio_value, format="audio/wav")

    if st.button("📊 Analyze pronunciation"):
        if not reference_text.strip():
            st.error("Please type, paste, upload, or select a French text first.")
        else:
            with st.spinner("Analyzing pronunciation..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                        tmp_wav.write(audio_value.read())
                        wav_path = tmp_wav.name

                    transcript = transcribe_audio_file(wav_path)

                    score = pronunciation_score(reference_text, transcript)
                    feedback = word_feedback(reference_text, transcript)
                    attempt_issue = detect_attempt_issue(reference_text, transcript, feedback)

                    if input_mode == "Teacher Texts":
                        auto_liaison_points = detect_liaison_candidates(reference_text)
                    else:
                        auto_liaison_points = []

                    coaching_message = generate_coaching_message(score, feedback, auto_liaison_points)

                    attempt = {
                        "timestamp": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "reference_text": reference_text,
                        "recognized_text": transcript,
                        "score": score,
                        "feedback": feedback,
                        "mode": input_mode,
                        "coaching_message": coaching_message
                    }

                    st.session_state.attempt_history.append(attempt)
                    st.session_state.attempt_history = st.session_state.attempt_history[-MAX_ATTEMPTS:]

                    save_attempt_to_db(current_user_id, current_lesson_id, attempt)

                    st.subheader("Results")
                    st.write(f"**Recognized text:** {transcript}")
                    st.write(f"**Pronunciation score:** {score}/100")
                    st.warning(attempt_issue)
                    render_coaching_message(coaching_message)

                    if input_mode == "Teacher Texts":
                        render_pronunciation_focus(
                            text=reference_text,
                            liaison_points=auto_liaison_points,
                            context="results",
                            current_user_id=current_user_id,
                            current_lesson_id=current_lesson_id,
                            phrase_history_key="phrase_history",
                            max_phrase_attempts=MAX_PHRASE_ATTEMPTS,
                            enable_phrase_recording=True,
                        )

                    st.markdown("### Word-by-word feedback")
                    st.markdown(render_colored_feedback_with_ipa(feedback), unsafe_allow_html=True)

                    st.markdown("### Legend")
                    st.markdown(
                        """
                        <span style="background-color:#16a34a;color:white;padding:5px 10px;border-radius:6px;">Good</span>
                        &nbsp;
                        <span style="background-color:#f59e0b;color:white;padding:5px 10px;border-radius:6px;">Close</span>
                        &nbsp;
                        <span style="background-color:#dc2626;color:white;padding:5px 10px;border-radius:6px;">Needs improvement</span>
                        """,
                        unsafe_allow_html=True
                    )

                    with st.expander("See detailed comparison"):
                        for item in feedback:
                            from speech import get_ipa
                            ipa = get_ipa(item.get("reference", ""))
                            st.write(
                                f"Reference: **{item.get('reference', '')}** | "
                                f"Heard: **{item.get('spoken', '—') or '—'}** | "
                                f"IPA: **/{ipa}/** | "
                                f"Match: **{item.get('similarity', 0)}%** | "
                                f"Status: **{item.get('status', 'improve')}**"
                            )

                except Exception as e:
                    st.error(f"Analysis failed: {e}")

# -----------------------------
# Progress dashboard
# -----------------------------
from db import get_progress_rows

st.markdown("---")
st.subheader("📊 My Progress")

if current_user_id is None:
    st.info("Sign in to see your progress dashboard.")
else:
    try:
        progress_rows = get_progress_rows(current_user_id)

        if progress_rows:
            total_attempts = sum(row["attempt_count"] for row in progress_rows)
            overall_best = max(float(row["best_score"]) for row in progress_rows)
            overall_avg = round(
                sum(float(row["average_score"]) for row in progress_rows) / len(progress_rows), 2
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("Lessons Practiced", len(progress_rows))
            c2.metric("Total Attempts", total_attempts)
            c3.metric("Best Score", f"{overall_best:.1f}")

            st.write(f"**Average across lessons:** {overall_avg:.1f}")
        else:
            st.info("No saved progress yet. Complete a lesson to start tracking progress.")
    except Exception:
        st.info("Progress dashboard will appear after your first saved attempt.")

# -----------------------------
# Session history
# -----------------------------
st.markdown("---")
st.subheader("📈 Session History")

if st.button("🗑 Clear session history"):
    st.session_state.attempt_history = []
    st.success("Session history cleared.")

if st.session_state.attempt_history:
    avg_score = sum(a["score"] for a in st.session_state.attempt_history) / len(st.session_state.attempt_history)
    st.metric("Average Score", f"{avg_score:.1f}")

    for i, attempt in enumerate(reversed(st.session_state.attempt_history), start=1):
        with st.expander(f"Attempt {i} — {attempt['timestamp']} — Score: {attempt['score']}/100"):
            st.write(f"**Mode:** {attempt.get('mode', 'Unknown')}")
            st.write(f"**Reference text:** {attempt.get('reference_text', '')}")
            st.write(f"**Recognized text:** {attempt.get('recognized_text', '')}")
            st.write(f"**Score:** {attempt.get('score', 0)}/100")

            st.markdown("**Word-by-word feedback:**")
            feedback_data = attempt.get("feedback", [])
            st.markdown(render_colored_feedback_with_ipa(feedback_data), unsafe_allow_html=True)
else:
    st.info("No attempts yet. Record and analyze a reading to build your history.")

st.markdown("---")
st.subheader("🎯 Phrase History")

if st.button("🗑 Clear phrase history"):
    st.session_state.phrase_history = []
    st.success("Phrase history cleared.")

if st.session_state.phrase_history:
    for i, item in enumerate(reversed(st.session_state.phrase_history), start=1):
        phrase_result = item.get("phrase_result", {})
        with st.expander(
            f"Phrase Attempt {i} — {phrase_result.get('timestamp', '')} — "
            f"{phrase_result.get('phrase', '')} — Score: {phrase_result.get('score', 0)}/100"
        ):
            st.write(f"**Reference text:** {item.get('reference_text', '')}")
            st.write(f"**Target phrase:** {phrase_result.get('phrase', '')}")
            st.write(f"**Recognized phrase:** {phrase_result.get('recognized_phrase', '')}")
            st.write(f"**Phrase score:** {phrase_result.get('score', 0)}/100")

            st.markdown("**Phrase word-by-word feedback:**")
            phrase_feedback = phrase_result.get("feedback", [])
            st.markdown(render_colored_feedback_with_ipa(phrase_feedback), unsafe_allow_html=True)
else:
    st.info("No phrase attempts yet. Record and analyze a highlighted phrase to build phrase history.")
