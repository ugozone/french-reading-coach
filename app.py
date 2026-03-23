import streamlit as st 
gtts import gTTS
import tempfile
import whisper
import re
from difflib import SequenceMatcher
from pypdf import PdfReader
import docx2txt
import os
from phonemizer import phonemize
from phonemizer.backend.espeak.wrapper import EspeakWrapper
import html
from datetime import datetime
from teacher_texts import TEACHER_TEXTS

import platform

if platform.system() == "Darwin":
    os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = "/opt/homebrew/lib/libespeak.dylib"
st.title("🇫🇷 French Reading Coach AI")
st.write(
    "Students can type, paste, or upload French text, or choose teacher texts by CEFR level, "
    "then listen, record themselves, and get pronunciation feedback with IPA support."
)

# -----------------------------
# Load Whisper model once
# -----------------------------
@st.cache_resource
def load_model():
    return whisper.load_model("small")

model = load_model()

# -----------------------------
# Helper functions
# -----------------------------
def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\sàâæçéèêëîïôœùûüÿñ'-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def pronunciation_score(reference: str, spoken: str) -> float:
    ref = normalize_text(reference)
    spk = normalize_text(spoken)
    return round(SequenceMatcher(None, ref, spk).ratio() * 100, 1)


def word_feedback(reference: str, spoken: str):
    ref_words = normalize_text(reference).split()
    spk_words = normalize_text(spoken).split()

    feedback = []
    max_len = len(ref_words)

    for i in range(max_len):
        ref_word = ref_words[i]
        spk_word = spk_words[i] if i < len(spk_words) else ""

        similarity = SequenceMatcher(None, ref_word, spk_word).ratio()

        if similarity >= 0.85:
            status = "good"
            color = "#16a34a"
        elif similarity >= 0.55:
            status = "close"
            color = "#f59e0b"
        else:
            status = "improve"
            color = "#dc2626"

        feedback.append({
            "reference": ref_word,
            "spoken": spk_word,
            "similarity": round(similarity * 100, 1),
            "status": status,
            "color": color
        })

    return feedback


def clean_word(word: str) -> str:
    if word is None:
        return ""
    return str(word).lower().strip(" ,;:!?.'\"()[]{}")


def get_ipa(word: str) -> str:
    try:
        if word is None:
            return "IPA unavailable"

        word = str(word).strip()
        if not word:
            return "IPA unavailable"

        ipa = phonemize(
            word,
            language="fr-fr",
            backend="espeak",
            strip=True
        )

        if ipa is None:
            return "IPA unavailable"

        ipa = str(ipa).strip()
        return ipa if ipa else "IPA unavailable"
    except Exception as e:
        return f"IPA unavailable ({e})"


def get_liaison_base_ipa(word: str) -> str:
    word = clean_word(word)

    special_bases = {
        "vous": "vu",
        "nous": "nu",
        "les": "le",
        "des": "de",
        "mes": "me",
        "tes": "te",
        "ses": "se",
        "nos": "no",
        "vos": "vo",
        "leurs": "lœʁ",
        "ils": "il",
        "elles": "ɛl",
        "deux": "dø",
        "trois": "tʁwa",
        "six": "si",
        "dix": "di",
        "comment": "kɔmɑ̃",
        "un": "œ̃",
        "bon": "bɔ̃",
        "grand": "gʁɑ̃",
        "petit": "pəti"
    }

    if word in special_bases:
        return special_bases[word]

    return get_ipa(word).strip("/")


def make_lesson_label(text_data: dict) -> str:
    title = text_data.get("title", "Untitled")
    unit = text_data.get("unit", "No unit")
    theme = text_data.get("theme", "No theme")
    level = text_data.get("level", "No level")
    return f"{title} — {unit} — {theme} — {level}"


def render_lesson_card(text_data: dict):
    st.markdown(
        f"""
        <div style="
            border: 1px solid #e5e7eb;
            background-color: #f9fafb;
            padding: 14px;
            border-radius: 12px;
            margin-bottom: 14px;
        ">
            <div style="font-size: 18px; font-weight: 700; color: #111827; margin-bottom: 8px;">
                {html.escape(text_data.get("title", "Untitled"))}
            </div>
            <div style="margin-bottom: 4px;"><strong>Level:</strong> {html.escape(text_data.get("level", ""))}</div>
            <div style="margin-bottom: 4px;"><strong>Unit:</strong> {html.escape(text_data.get("unit", ""))}</div>
            <div style="margin-bottom: 4px;"><strong>Theme:</strong> {html.escape(text_data.get("theme", ""))}</div>
            <div style="margin-bottom: 4px;"><strong>Pronunciation focus:</strong> {html.escape(text_data.get("focus", ""))}</div>
            <div style="margin-bottom: 4px;"><strong>Grammar focus:</strong> {html.escape(text_data.get("grammar_focus", ""))}</div>
            <div style="margin-bottom: 4px;"><strong>Skills:</strong> {html.escape(", ".join(text_data.get("skills", [])))}</div>
            <div style="margin-bottom: 4px;"><strong>Teacher tip:</strong> {html.escape(text_data.get("teacher_tip", ""))}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def play_phrase_audio(phrase: str, key_suffix: str, label: str = None):
    try:
        tts = gTTS(phrase, lang="fr")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
            tts.save(tmp_mp3.name)

            button_label = label if label else f"🔊 Hear only: {phrase}"

            if st.button(button_label, key=f"play_phrase_{key_suffix}"):
                st.audio(tmp_mp3.name, format="audio/mp3")
    except Exception as e:
        st.error(f"Could not generate phrase audio: {e}")


def analyze_phrase_pronunciation(phrase: str, audio_file, model, key_prefix: str):
    if audio_file is None:
        return None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
            tmp_wav.write(audio_file.read())
            wav_path = tmp_wav.name

        result = model.transcribe(
            wav_path,
            language="fr",
            task="transcribe",
            fp16=False,
            temperature=0
        )
        transcript = result["text"].strip()

        score = pronunciation_score(phrase, transcript)
        feedback = word_feedback(phrase, transcript)

        st.markdown("#### Phrase analysis")
        st.write(f"**Target phrase:** {phrase}")
        st.write(f"**Recognized phrase:** {transcript}")
        st.write(f"**Phrase score:** {score}/100")

        st.markdown("**Phrase word-by-word feedback**")
        st.html(render_colored_feedback_with_ipa(feedback))

        with st.expander(f"See detailed phrase comparison ({key_prefix})"):
            for item in feedback:
                ipa = get_ipa(item.get("reference", ""))
                st.write(
                    f"Reference: **{item.get('reference', '')}** | "
                    f"Heard: **{item.get('spoken', '—') or '—'}** | "
                    f"IPA: **/{ipa}/** | "
                    f"Match: **{item.get('similarity', 0)}%** | "
                    f"Status: **{item.get('status', 'improve')}**"
                )

        return {
            "phrase": phrase,
            "recognized_phrase": transcript,
            "score": score,
            "feedback": feedback,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        st.error(f"Phrase analysis failed: {e}")
        return None


def render_colored_feedback_with_ipa(feedback):
    html_words = []

    for item in feedback:
        reference_word = item.get("reference", "")
        if reference_word is None:
            reference_word = ""
        reference_word = str(reference_word)

        ipa = get_ipa(reference_word)
        if ipa is None:
            ipa = "IPA unavailable"
        ipa = str(ipa)

        status = item.get("status", "improve")
        color = item.get("color", "#dc2626")

        if status == "good":
            ipa_color = "#374151"
            ipa_weight = "500"
        elif status == "close":
            ipa_color = "#b45309"
            ipa_weight = "600"
        else:
            ipa_color = "#b91c1c"
            ipa_weight = "700"

        ipa_html = f"""
            <div style="
                font-size: 13px;
                color: {ipa_color};
                margin-top: 6px;
                font-weight: {ipa_weight};
            ">
                /{html.escape(ipa)}/
            </div>
        """

        html_words.append(
            f"""
            <div style="
                display: inline-block;
                text-align: center;
                margin: 6px;
                vertical-align: top;
            ">
                <div style="
                    background-color: {color};
                    color: white;
                    padding: 8px 12px;
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 16px;
                    min-width: 70px;
                ">
                    {html.escape(reference_word)}
                </div>
                {ipa_html}
            </div>
            """
        )

    return " ".join(html_words)


def extract_text_from_pdf(uploaded_file):
    text = ""
    reader = PdfReader(uploaded_file)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    text = docx2txt.process(tmp_path)
    os.remove(tmp_path)
    return text.strip()


def extract_text_from_txt(uploaded_file):
    return uploaded_file.read().decode("utf-8").strip()


def starts_with_vowel_or_silent_h(word: str) -> bool:
    word = clean_word(word)
    if not word:
        return False
    vowels = "aàâæeéèêëiîïoôœuùûüüyÿh"
    return word[0] in vowels


def detect_liaison_candidates(text: str):
    words = text.split()
    candidates = []

    obligatory_first_words = {
        "les", "des", "mes", "tes", "ses", "nos", "vos", "leurs",
        "nous", "vous", "ils", "elles",
        "un", "deux", "trois", "six", "dix",
        "petit", "grand", "bon", "comment"
    }

    known_connected_ipa = {
        "comment allez-vous": {
            "connected_ipa": "/kɔmɑ̃.t‿ale.vu/",
            "focus_sound": "t‿a",
            "tip": "Link the final sound of 'comment' smoothly to 'allez-vous'."
        },
        "les amis": {
            "connected_ipa": "/le.z‿ami/",
            "focus_sound": "z‿a",
            "tip": "Pronounce the liaison /z/ between 'les' and 'amis'."
        },
        "nous avons": {
            "connected_ipa": "/nu.z‿avɔ̃/",
            "focus_sound": "z‿a",
            "tip": "Link 'nous' to 'avons' with a clear /z/."
        },
        "ils ont": {
            "connected_ipa": "/il.z‿ɔ̃/",
            "focus_sound": "z‿ɔ̃",
            "tip": "Pronounce the liaison /z/ before 'ont'."
        },
        "huit heures": {
            "connected_ipa": "/ɥit‿œʁ/",
            "focus_sound": "t‿œ",
            "tip": "Make the /t/ connection audible before 'heures'."
        },
        "six heures": {
            "connected_ipa": "/si.z‿œʁ/",
            "focus_sound": "z‿œ",
            "tip": "Pronounce the linking /z/ before 'heures'."
        },
        "vous avez": {
            "connected_ipa": "/vu.z‿ave/",
            "focus_sound": "z‿a",
            "tip": "Link 'vous' to 'avez' with a clear /z/."
        },
        "vous appelez": {
            "connected_ipa": "/vu.z‿aple/",
            "focus_sound": "z‿a",
            "tip": "Link 'vous' to 'appelez' with a clear /z/."
        },
        "vous habitez": {
            "connected_ipa": "/vu.z‿abite/",
            "focus_sound": "z‿a",
            "tip": "Link 'vous' to 'habitez' with a clear /z/."
        },
        "des amis": {
            "connected_ipa": "/de.z‿ami/",
            "focus_sound": "z‿a",
            "tip": "Pronounce the liaison /z/ between 'des' and 'amis'."
        }
    }

    for i in range(len(words) - 1):
        w1 = clean_word(words[i])
        w2 = clean_word(words[i + 1])

        if not w1 or not w2:
            continue

        phrase = f"{w1} {w2}"

        if phrase in known_connected_ipa:
            candidates.append({
                "phrase": phrase,
                "connected_ipa": known_connected_ipa[phrase]["connected_ipa"],
                "focus_sound": known_connected_ipa[phrase]["focus_sound"],
                "tip": known_connected_ipa[phrase]["tip"]
            })
            continue

        if w1 in obligatory_first_words and starts_with_vowel_or_silent_h(w2):
            word1_ipa = get_liaison_base_ipa(w1)
            word2_ipa = get_ipa(w2).strip("/")

            liaison_sound = ""
            if w1.endswith(("s", "x", "z")):
                liaison_sound = "z"
            elif w1.endswith(("t", "d")):
                liaison_sound = "t"
            elif w1.endswith("n"):
                liaison_sound = "n"
            elif w1.endswith("r"):
                liaison_sound = "ʁ"
            elif w1.endswith("p"):
                liaison_sound = "p"

            if liaison_sound:
                connected_ipa = f"/{word1_ipa}.{liaison_sound}‿{word2_ipa}/"
                focus_sound = f"{liaison_sound}‿{word2_ipa[0] if word2_ipa else ''}"
            else:
                connected_ipa = f"/{word1_ipa}‿{word2_ipa}/"
                focus_sound = "linked boundary"

            candidates.append({
                "phrase": phrase,
                "connected_ipa": connected_ipa,
                "focus_sound": focus_sound,
                "tip": f"Try to connect '{w1}' smoothly to '{w2}'."
            })

    unique_candidates = []
    seen = set()
    for c in candidates:
        if c["phrase"] not in seen:
            unique_candidates.append(c)
            seen.add(c["phrase"])

    return unique_candidates


def highlight_liaison_phrases(text: str, liaison_points: list) -> str:
    highlighted_text = html.escape(text)

    for point in liaison_points:
        phrase = point["phrase"]
        escaped_phrase = html.escape(phrase)
        highlighted_text = highlighted_text.replace(
            escaped_phrase,
            f"""
            <span style="
                background-color: #fef3c7;
                color: #92400e;
                padding: 2px 6px;
                border-radius: 6px;
                font-weight: 600;
            ">
                {escaped_phrase}
            </span>
            """
        )

    return highlighted_text


def render_pronunciation_focus(text: str, liaison_points: list, context: str):
    if not liaison_points:
        return

    st.markdown("### 🎯 Pronunciation focus (Connected speech)")

    highlighted = highlight_liaison_phrases(text, liaison_points)

    st.markdown(
        f"""
        <div style="
            font-size: 18px;
            margin-bottom: 16px;
            line-height: 1.7;
        ">
            {highlighted}
        </div>
        """,
        unsafe_allow_html=True
    )

    for idx, point in enumerate(liaison_points):
        phrase = point["phrase"]
        words = phrase.split()
        word_ipas = [get_ipa(w) for w in words]
        breakdown = " + ".join([f"/{ipa}/" for ipa in word_ipas])

        st.markdown(
            f"""
            <div style="
                border: 1px solid #e5e7eb;
                background-color: #f9fafb;
                padding: 14px;
                border-radius: 12px;
                margin-bottom: 10px;
            ">
                <div style="
                    font-weight: 700;
                    font-size: 16px;
                    margin-bottom: 8px;
                    color: #111827;
                ">
                    {html.escape(phrase)}
                </div>
                <div style="margin-bottom: 6px;">
                    🔊 <strong>Connected:</strong> {html.escape(point["connected_ipa"])}
                </div>
                <div style="margin-bottom: 6px;">
                    🧩 <strong>Breakdown:</strong> {html.escape(breakdown)}
                </div>
                <div style="margin-bottom: 6px;">
                    🎯 <strong>Focus:</strong> {html.escape(point["focus_sound"])}
                </div>
                <div style="margin-bottom: 10px;">
                    💡 <strong>Tip:</strong> {html.escape(point["tip"])}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.caption("Practice this connected phrase separately before reading the whole sentence again.")

        play_phrase_audio(
            phrase,
            key_suffix=f"{context}_{idx}_{clean_word(phrase)}",
            label=f"🔊 Hear only: {phrase}"
        )

        phrase_audio = st.audio_input(
            f"🎤 Record only this phrase: {phrase}",
            key=f"phrase_audio_{context}_{idx}_{clean_word(phrase)}"
        )

        if phrase_audio is not None:
            st.audio(phrase_audio, format="audio/wav")

            if st.button(
                f"📊 Analyze phrase: {phrase}",
                key=f"analyze_phrase_{context}_{idx}_{clean_word(phrase)}"
            ):
                phrase_result = analyze_phrase_pronunciation(
                    phrase=phrase,
                    audio_file=phrase_audio,
                    model=model,
                    key_prefix=f"{context}_{idx}_{clean_word(phrase)}"
                )

                if phrase_result is not None:
                    st.session_state.phrase_history.append({
                        "context": context,
                        "reference_text": text,
                        "phrase_result": phrase_result
                    })


def detect_attempt_issue(reference_text: str, transcript: str, feedback: list) -> str:
    ref_words = normalize_text(reference_text).split()
    heard_words = normalize_text(transcript).split()

    if len(heard_words) == 0:
        return "No speech was clearly recognized. Try recording again in a quieter space."

    if len(heard_words) < max(1, len(ref_words) // 2):
        return "Only part of the sentence was recognized. Try saying the full sentence more clearly and without long pauses."

    improve_count = sum(1 for item in feedback if item["status"] == "improve")
    if improve_count >= max(2, len(feedback) // 2):
        return "Several words were not recognized clearly. Speak a little slower and articulate each word more fully."

    return "The recording was captured, but some words need clearer pronunciation."

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
# Input mode
# -----------------------------
input_mode = st.radio(
    "Choose text source:",
    ["My Text", "Teacher Texts"]
)

# -----------------------------
# Input section
# -----------------------------
st.subheader("Choose how to add French text")

selected_text_data = None
auto_liaison_points = []

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
        height=250
    )
    st.session_state.reference_text = reference_text

else:
    selected_level = st.selectbox(
        "Choose CEFR level:",
        ["A1", "A2", "B1", "B2", "C1", "C2"]
    )

    filtered_texts = [t for t in TEACHER_TEXTS if t["level"] == selected_level]

    lesson_options = {make_lesson_label(t): t for t in filtered_texts}

    selected_label = st.selectbox(
        "Choose a lesson:",
        list(lesson_options.keys())
    )

    selected_text_data = lesson_options[selected_label]

    render_lesson_card(selected_text_data)

    reference_text = st.text_area(
        "Teacher text:",
        value=selected_text_data["text"],
        height=250
    )
    st.session_state.reference_text = reference_text

    auto_liaison_points = detect_liaison_candidates(reference_text)
    render_pronunciation_focus(reference_text, auto_liaison_points, context="preview")

# -----------------------------
# Listen to pronunciation
# -----------------------------
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
# Record audio in browser
# -----------------------------
audio_value = st.audio_input("🎤 Record your pronunciation")

if audio_value is not None:
    st.audio(audio_value, format="audio/wav")

    if st.button("📊 Analyze pronunciation"):
        if not reference_text.strip():
            st.error("Please type, paste, upload, or select a French text first.")
        else:
            with st.spinner("Analyzing with Whisper..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                        tmp_wav.write(audio_value.read())
                        wav_path = tmp_wav.name

                    result = model.transcribe(
                        wav_path,
                        language="fr",
                        task="transcribe",
                        fp16=False,
                        temperature=0
                    )
                    transcript = result["text"].strip()

                    score = pronunciation_score(reference_text, transcript)
                    feedback = word_feedback(reference_text, transcript)
                    attempt_issue = detect_attempt_issue(reference_text, transcript, feedback)

                    attempt = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "reference_text": reference_text,
                        "recognized_text": transcript,
                        "score": score,
                        "feedback": feedback,
                        "mode": input_mode
                    }
                    st.session_state.attempt_history.append(attempt)

                    st.subheader("Results")
                    st.write(f"**Recognized text:** {transcript}")
                    st.write(f"**Pronunciation score:** {score}/100")
                    st.warning(attempt_issue)

                    if input_mode == "Teacher Texts":
                        auto_liaison_points = detect_liaison_candidates(reference_text)
                        render_pronunciation_focus(reference_text, auto_liaison_points, context="results")

                    st.markdown("### Word-by-word feedback")
                    st.html(render_colored_feedback_with_ipa(feedback))

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
# Session history
# -----------------------------
st.markdown("---")
st.subheader("📈 Session History")

if st.button("🗑 Clear session history"):
    st.session_state.attempt_history = []
    st.success("Session history cleared.")

if st.session_state.attempt_history:
    for i, attempt in enumerate(reversed(st.session_state.attempt_history), start=1):
        with st.expander(f"Attempt {i} — {attempt['timestamp']} — Score: {attempt['score']}/100"):
            st.write(f"**Mode:** {attempt.get('mode', 'Unknown')}")
            st.write(f"**Reference text:** {attempt.get('reference_text', '')}")
            st.write(f"**Recognized text:** {attempt.get('recognized_text', '')}")
            st.write(f"**Score:** {attempt.get('score', 0)}/100")

            st.markdown("**Word-by-word feedback:**")
            feedback_data = attempt.get("feedback", [])
            st.html(render_colored_feedback_with_ipa(feedback_data))
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
            st.html(render_colored_feedback_with_ipa(phrase_feedback))
else:
    st.info("No phrase attempts yet. Record and analyze a highlighted phrase to build phrase history.")
