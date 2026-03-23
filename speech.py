import os
import html
import tempfile
import re
from difflib import SequenceMatcher
from pypdf import PdfReader
import docx2txt
import whisper
import streamlit as st

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


@st.cache_resource
def load_model():
    return whisper.load_model("tiny")


model = load_model()


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


def fallback_transcription(audio_path: str) -> str:
    try:
        result = model.transcribe(audio_path, language="fr", fp16=False)
        return result["text"].strip()
    except Exception as e:
        st.error(f"Fallback transcription failed: {e}")
        return ""


def transcribe_audio_file(audio_path: str) -> str:
    return fallback_transcription(audio_path)


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
