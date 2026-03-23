import streamlit as st 
from gtts import gTTS
import tempfile
import re
from difflib import SequenceMatcher
from pypdf import PdfReader
import docx2txt
import os
import html
import time
import uuid
import requests
from datetime import datetime
import boto3
from supabase import create_client, Client

from teacher_texts import TEACHER_TEXTS

# =========================================================
# Streamlit config
# =========================================================
st.set_page_config(page_title="French Reading Coach AI", page_icon="🇫🇷")

st.title("🇫🇷 French Reading Coach AI")
st.write(
    "Students can type, paste, or upload French text, or choose teacher texts by CEFR level, "
    "then listen, record themselves, and get pronunciation feedback."
)

# =========================================================
# Config from Streamlit secrets or environment
# =========================================================
def get_secret(name: str, default: str = "") -> str:
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, default)


AWS_REGION = get_secret("AWS_REGION", "")
AWS_S3_BUCKET = get_secret("AWS_S3_BUCKET", "")
MAX_ATTEMPTS = 10
MAX_PHRASE_ATTEMPTS = 20

SUPABASE_URL = get_secret("SUPABASE_URL", "")
SUPABASE_KEY = get_secret("SUPABASE_KEY", "")

# =========================================================
# Optional IPA support
# =========================================================
PHONEMIZER_AVAILABLE = False
try:
    from phonemizer import phonemize
    from phonemizer.backend.espeak.wrapper import EspeakWrapper
    import platform

    if platform.system() == "Darwin":
        mac_espeak = "/opt/homebrew/lib/libespeak.dylib"
        if os.path.exists(mac_espeak):
            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = mac_espeak
            EspeakWrapper.set_library(mac_espeak)

    PHONEMIZER_AVAILABLE = True
except Exception:
    PHONEMIZER_AVAILABLE = False

# =========================================================
# Cached clients
# =========================================================
@st.cache_resource
def get_aws_clients():
    if not AWS_REGION or not AWS_S3_BUCKET:
        return None

    return {
        "s3": boto3.client("s3", region_name=AWS_REGION),
        "transcribe": boto3.client("transcribe", region_name=AWS_REGION),
    }


@st.cache_resource
def get_supabase() -> Client | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


aws_clients = get_aws_clients()
supabase = get_supabase()

# =========================================================
# Helper functions
# =========================================================
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
    if not PHONEMIZER_AVAILABLE:
        return "IPA unavailable"

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
    except Exception:
        return "IPA unavailable"


def render_colored_feedback_with_ipa(feedback):
    html_words = []

    for item in feedback:
        reference_word = str(item.get("reference", "") or "")
        ipa = get_ipa(reference_word)
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
            <div style="margin-bottom: 4px;"><strong>Skills:</strong> {html.escape(', '.join(text_data.get("skills", [])))}</div>
            <div style="margin-bottom: 4px;"><strong>Teacher tip:</strong> {html.escape(text_data.get("teacher_tip", ""))}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


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

            candidates.append({
                "phrase": phrase,
                "connected_ipa": "Connected pronunciation target",
                "focus_sound": liaison_sound if liaison_sound else "linked boundary",
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


def play_phrase_audio(phrase: str, key_suffix: str, label: str = None):
    try:
        button_label = label if label else f"🔊 Hear only: {phrase}"

        if st.button(button_label, key=f"play_phrase_{key_suffix}"):
            tts = gTTS(phrase, lang="fr")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
                tts.save(tmp_mp3.name)
                st.audio(tmp_mp3.name, format="audio/mp3")
    except Exception as e:
        st.error(f"Could not generate phrase audio: {e}")


def upload_audio_to_s3(audio_bytes: bytes, suffix: str = ".wav") -> str:
    if aws_clients is None:
        raise RuntimeError("AWS is not configured. Set AWS_REGION and AWS_S3_BUCKET.")

    key = f"transcribe-input/{uuid.uuid4().hex}{suffix}"
    aws_clients["s3"].put_object(
        Bucket=AWS_S3_BUCKET,
        Key=key,
        Body=audio_bytes,
        ContentType="audio/wav"
    )
    return f"s3://{AWS_S3_BUCKET}/{key}"


def transcribe_audio_with_aws(audio_bytes: bytes, media_format: str = "wav", language_code: str = "fr-FR") -> str:
    if aws_clients is None:
        raise RuntimeError("AWS is not configured. Set AWS_REGION and AWS_S3_BUCKET.")

    s3_uri = upload_audio_to_s3(audio_bytes, suffix=f".{media_format}")
    job_name = f"fr-coach-{uuid.uuid4().hex}"

    aws_clients["transcribe"].start_transcription_job(
        TranscriptionJobName=job_name,
        LanguageCode=language_code,
        MediaFormat=media_format,
        Media={"MediaFileUri": s3_uri}
    )

    start = time.time()
    while True:
        job = aws_clients["transcribe"].get_transcription_job(TranscriptionJobName=job_name)
        status = job["TranscriptionJob"]["TranscriptionJobStatus"]

        if status in ["COMPLETED", "FAILED"]:
            break

        if time.time() - start > 180:
            raise TimeoutError("Transcription job timed out.")
        time.sleep(2)

    if status == "FAILED":
        raise RuntimeError(job["TranscriptionJob"].get("FailureReason", "AWS Transcribe failed."))

    transcript_uri = job["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
    transcript_json = requests.get(transcript_uri, timeout=30).json()
    return transcript_json["results"]["transcripts"][0]["transcript"]


def generate_coaching_message(score: float, feedback: list, liaison_points: list | None = None) -> str:
    if liaison_points is None:
        liaison_points = []

    weak_words = [item["reference"] for item in feedback if item.get("status") == "improve"]
    close_words = [item["reference"] for item in feedback if item.get("status") == "close"]

    liaison_tip = ""
    if liaison_points:
        first_point = liaison_points[0]
        liaison_tip = (
            f" Pay special attention to the connected phrase "
            f"'{first_point['phrase']}' and the focus sound '{first_point['focus_sound']}'."
        )

    if score >= 95:
        return "Excellent work. Your pronunciation was very strong overall." + liaison_tip
    elif score >= 80:
        if weak_words:
            return (
                f"Good job. Improve a few words: {', '.join(weak_words[:4])}."
                + liaison_tip
                + " Repeat the highlighted phrase once more, then read the full sentence again."
            )
        return "Good job overall." + liaison_tip
    elif score >= 60:
        focus_words = weak_words[:4] if weak_words else close_words[:4]
        if focus_words:
            return (
                f"You are getting closer. Focus on these words: {', '.join(focus_words)}."
                + liaison_tip
                + " Practice the target phrase separately before reading the whole sentence again."
            )
        return "You are getting closer." + liaison_tip
    else:
        focus_words = weak_words[:4] if weak_words else close_words[:4]
        if focus_words:
            return (
                f"This sentence needs more practice. Start with: {', '.join(focus_words)}."
                + liaison_tip
                + " Listen again, repeat the highlighted phrase slowly, and record again."
            )
        return "This sentence needs more practice." + liaison_tip


def render_coaching_message(message: str):
    st.markdown(
        f"""
        <div style="
            border: 1px solid #bfdbfe;
            background-color: #eff6ff;
            padding: 14px;
            border-radius: 12px;
            margin-top: 12px;
            margin-bottom: 16px;
            color: #1e3a8a;
            font-size: 16px;
            line-height: 1.6;
        ">
            <strong>🧠 Coaching message</strong><br>
            {html.escape(message)}
        </div>
        """,
        unsafe_allow_html=True
    )


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

# =========================================================
# Supabase helpers
# =========================================================
def auth_ready() -> bool:
    return supabase is not None


def sign_up_user(email: str, password: str, full_name: str = ""):
    if supabase is None:
        raise RuntimeError("Supabase is not configured.")
    return supabase.auth.sign_up(
        {
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}},
        }
    )


def sign_in_user(email: str, password: str):
    if supabase is None:
        raise RuntimeError("Supabase is not configured.")
    return supabase.auth.sign_in_with_password(
        {
            "email": email,
            "password": password,
        }
    )


def sign_out_user():
    if supabase is not None:
        supabase.auth.sign_out()


def get_current_user():
    if supabase is None:
        return None
    try:
        user_response = supabase.auth.get_user()
        return user_response.user
    except Exception:
        return None


def lesson_key_from_text(text_data: dict) -> str:
    title = text_data.get("title", "").strip().lower().replace(" ", "_")
    level = text_data.get("level", "").strip().lower()
    return f"{level}__{title}"


def ensure_lessons_seeded():
    if supabase is None:
        return

    rows = []
    for item in TEACHER_TEXTS:
        rows.append({
            "lesson_key": lesson_key_from_text(item),
            "title": item.get("title", ""),
            "unit": item.get("unit", ""),
            "theme": item.get("theme", ""),
            "level": item.get("level", ""),
            "focus": item.get("focus", ""),
            "grammar_focus": item.get("grammar_focus", ""),
            "text_content": item.get("text", ""),
            "teacher_tip": item.get("teacher_tip", ""),
        })

    try:
        supabase.table("lessons").upsert(rows, on_conflict="lesson_key").execute()
    except Exception:
        pass


def get_lesson_id_for_text(selected_text_data: dict):
    if supabase is None or selected_text_data is None:
        return None

    key = lesson_key_from_text(selected_text_data)
    try:
        result = supabase.table("lessons").select("id").eq("lesson_key", key).limit(1).execute()
        if result.data:
            return result.data[0]["id"]
    except Exception:
        pass
    return None


def update_progress_summary(user_id: str, lesson_id):
    if supabase is None or lesson_id is None:
        return

    try:
        attempts = (
            supabase.table("attempts")
            .select("score, created_at")
            .eq("user_id", user_id)
            .eq("lesson_id", lesson_id)
            .order("created_at")
            .execute()
        )

        rows = attempts.data or []
        if not rows:
            return

        scores = [float(r["score"]) for r in rows]
        best_score = max(scores)
        average_score = round(sum(scores) / len(scores), 2)
        attempt_count = len(scores)
        last_practiced_at = rows[-1]["created_at"]

        supabase.table("progress_summary").upsert(
            {
                "user_id": user_id,
                "lesson_id": lesson_id,
                "best_score": best_score,
                "average_score": average_score,
                "attempt_count": attempt_count,
                "last_practiced_at": last_practiced_at,
            },
            on_conflict="user_id,lesson_id"
        ).execute()
    except Exception:
        pass


def save_attempt_to_db(user_id: str, lesson_id, attempt: dict):
    if supabase is None or user_id is None:
        return

    try:
        attempt_row = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "mode": attempt.get("mode", "Unknown"),
            "reference_text": attempt.get("reference_text", ""),
            "recognized_text": attempt.get("recognized_text", ""),
            "score": attempt.get("score", 0),
            "coaching_message": attempt.get("coaching_message", ""),
        }

        attempt_insert = supabase.table("attempts").insert(attempt_row).execute()
        attempt_id = attempt_insert.data[0]["id"]

        feedback_rows = []
        for item in attempt.get("feedback", []):
            feedback_rows.append({
                "attempt_id": attempt_id,
                "reference_word": item.get("reference", ""),
                "spoken_word": item.get("spoken", ""),
                "similarity": item.get("similarity", 0),
                "status": item.get("status", ""),
            })

        if feedback_rows:
            supabase.table("attempt_feedback").insert(feedback_rows).execute()

        update_progress_summary(user_id, lesson_id)
    except Exception:
        pass


def save_phrase_attempt_to_db(user_id: str, lesson_id, reference_text: str, phrase_result: dict):
    if supabase is None or user_id is None:
        return

    try:
        phrase_row = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "reference_text": reference_text,
            "phrase": phrase_result.get("phrase", ""),
            "recognized_phrase": phrase_result.get("recognized_phrase", ""),
            "score": phrase_result.get("score", 0),
        }

        phrase_insert = supabase.table("phrase_attempts").insert(phrase_row).execute()
        phrase_attempt_id = phrase_insert.data[0]["id"]

        feedback_rows = []
        for item in phrase_result.get("feedback", []):
            feedback_rows.append({
                "phrase_attempt_id": phrase_attempt_id,
                "reference_word": item.get("reference", ""),
                "spoken_word": item.get("spoken", ""),
                "similarity": item.get("similarity", 0),
                "status": item.get("status", ""),
            })

        if feedback_rows:
            supabase.table("phrase_feedback").insert(feedback_rows).execute()

        update_progress_summary(user_id, lesson_id)
    except Exception:
        pass

# =========================================================
# Phrase analysis
# =========================================================
def analyze_phrase_pronunciation(
    phrase: str,
    audio_file,
    key_prefix: str,
    current_user_id: str | None,
    current_lesson_id,
    reference_text: str
):
    if audio_file is None:
        return None

    try:
        audio_bytes = audio_file.read()
        transcript = transcribe_audio_with_aws(audio_bytes, media_format="wav", language_code="fr-FR")

        score = pronunciation_score(phrase, transcript)
        feedback = word_feedback(phrase, transcript)
        coaching_message = generate_coaching_message(score, feedback, [])

        st.markdown("#### Phrase analysis")
        st.write(f"**Target phrase:** {phrase}")
        st.write(f"**Recognized phrase:** {transcript}")
        st.write(f"**Phrase score:** {score}/100")
        render_coaching_message(coaching_message)

        st.markdown("**Phrase word-by-word feedback**")
        st.markdown(render_colored_feedback_with_ipa(feedback), unsafe_allow_html=True)

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

        phrase_result = {
            "phrase": phrase,
            "recognized_phrase": transcript,
            "score": score,
            "feedback": feedback,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if current_user_id:
            save_phrase_attempt_to_db(current_user_id, current_lesson_id, reference_text, phrase_result)

        return phrase_result

    except Exception as e:
        st.error(f"Phrase analysis failed: {e}")
        return None


def render_pronunciation_focus(
    text: str,
    liaison_points: list,
    context: str,
    current_user_id: str | None,
    current_lesson_id
):
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
                    key_prefix=f"{context}_{idx}_{clean_word(phrase)}",
                    current_user_id=current_user_id,
                    current_lesson_id=current_lesson_id,
                    reference_text=text
                )

                if phrase_result is not None:
                    st.session_state.phrase_history.append({
                        "context": context,
                        "reference_text": text,
                        "phrase_result": phrase_result
                    })
                    st.session_state.phrase_history = st.session_state.phrase_history[-MAX_PHRASE_ATTEMPTS:]

# =========================================================
# Session state
# =========================================================
default_text = "Bonjour, comment allez-vous aujourd'hui ?"

if "reference_text" not in st.session_state:
    st.session_state.reference_text = default_text

if "attempt_history" not in st.session_state:
    st.session_state.attempt_history = []

if "phrase_history" not in st.session_state:
    st.session_state.phrase_history = []

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Sign In"

# =========================================================
# Authentication UI
# =========================================================
st.sidebar.header("Account")

if not auth_ready():
    st.sidebar.warning("Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY in Streamlit secrets.")
    current_user = None
else:
    auth_mode = st.sidebar.radio("Choose", ["Sign In", "Sign Up"], key="auth_mode")

    if auth_mode == "Sign Up":
        signup_name = st.sidebar.text_input("Full name")
        signup_email = st.sidebar.text_input("Email", key="signup_email")
        signup_password = st.sidebar.text_input("Password", type="password", key="signup_password")

        if st.sidebar.button("Create account"):
            try:
                result = sign_up_user(signup_email, signup_password, signup_name)
                if result.user:
                    st.sidebar.success("Account created. Check your email if confirmation is enabled.")
                else:
                    st.sidebar.warning("Signup submitted.")
            except Exception as e:
                st.sidebar.error(f"Sign up failed: {e}")

    else:
        signin_email = st.sidebar.text_input("Email", key="signin_email")
        signin_password = st.sidebar.text_input("Password", type="password", key="signin_password")

        if st.sidebar.button("Sign in"):
            try:
                result = sign_in_user(signin_email, signin_password)
                if result.user:
                    st.sidebar.success("Signed in.")
                    st.rerun()
                else:
                    st.sidebar.error("Sign in failed.")
            except Exception as e:
                st.sidebar.error(f"Sign in failed: {e}")

    current_user = get_current_user()

    if current_user:
        st.sidebar.success(f"Logged in as {current_user.email}")
        if st.sidebar.button("Sign out"):
            sign_out_user()
            st.rerun()

if current_user is None:
    st.info("Please sign in to save and track progress.")
    st.stop()

ensure_lessons_seeded()

# =========================================================
# Input mode
# =========================================================
input_mode = st.radio(
    "Choose text source:",
    ["My Text", "Teacher Texts"]
)

# =========================================================
# Input section
# =========================================================
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
        reference_text,
        auto_liaison_points,
        context="preview",
        current_user_id=current_user.id,
        current_lesson_id=current_lesson_id
    )

# =========================================================
# Listen to pronunciation
# =========================================================
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

# =========================================================
# Record and analyze full sentence
# =========================================================
if aws_clients is None:
    st.warning("AWS transcription is not configured yet. Add AWS secrets in Streamlit Cloud.")
else:
    audio_value = st.audio_input("🎤 Record your pronunciation")

    if audio_value is not None:
        st.audio(audio_value, format="audio/wav")

        if st.button("📊 Analyze pronunciation"):
            if not reference_text.strip():
                st.error("Please type, paste, upload, or select a French text first.")
            else:
                with st.spinner("Analyzing with AWS Transcribe..."):
                    try:
                        audio_bytes = audio_value.read()
                        transcript = transcribe_audio_with_aws(
                            audio_bytes,
                            media_format="wav",
                            language_code="fr-FR"
                        )

                        score = pronunciation_score(reference_text, transcript)
                        feedback = word_feedback(reference_text, transcript)
                        attempt_issue = detect_attempt_issue(reference_text, transcript, feedback)

                        if input_mode == "Teacher Texts":
                            auto_liaison_points = detect_liaison_candidates(reference_text)
                        else:
                            auto_liaison_points = []

                        coaching_message = generate_coaching_message(score, feedback, auto_liaison_points)

                        attempt = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "reference_text": reference_text,
                            "recognized_text": transcript,
                            "score": score,
                            "feedback": feedback,
                            "mode": input_mode,
                            "coaching_message": coaching_message
                        }

                        st.session_state.attempt_history.append(attempt)
                        st.session_state.attempt_history = st.session_state.attempt_history[-MAX_ATTEMPTS:]

                        save_attempt_to_db(current_user.id, current_lesson_id, attempt)

                        st.subheader("Results")
                        st.write(f"**Recognized text:** {transcript}")
                        st.write(f"**Pronunciation score:** {score}/100")
                        st.warning(attempt_issue)
                        render_coaching_message(coaching_message)

                        if input_mode == "Teacher Texts":
                            render_pronunciation_focus(
                                reference_text,
                                auto_liaison_points,
                                context="results",
                                current_user_id=current_user.id,
                                current_lesson_id=current_lesson_id
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

# =========================================================
# Progress dashboard
# =========================================================
st.markdown("---")
st.subheader("📊 My Progress")

try:
    progress_rows = (
        supabase.table("progress_summary")
        .select("best_score, average_score, attempt_count, last_practiced_at, lesson_id")
        .eq("user_id", current_user.id)
        .execute()
    )

    if progress_rows.data:
        total_attempts = sum(row["attempt_count"] for row in progress_rows.data)
        overall_best = max(float(row["best_score"]) for row in progress_rows.data)
        overall_avg = round(
            sum(float(row["average_score"]) for row in progress_rows.data) / len(progress_rows.data), 2
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Lessons Practiced", len(progress_rows.data))
        c2.metric("Total Attempts", total_attempts)
        c3.metric("Best Score", f"{overall_best:.1f}")

        st.write(f"**Average across lessons:** {overall_avg:.1f}")
    else:
        st.info("No saved progress yet. Complete a lesson to start tracking progress.")
except Exception:
    st.info("Progress dashboard will appear after your first saved attempt.")

# =========================================================
# Session history
# =========================================================
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
