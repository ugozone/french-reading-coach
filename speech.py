import os
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
            "color": color,
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
            strip=True,
        )

        if ipa is None:
            return "IPA unavailable"

        ipa = str(ipa).strip()
        return ipa if ipa else "IPA unavailable"
    except Exception:
        return "IPA unavailable"


def transcribe_audio_file(audio_path: str) -> str:
    try:
        result = model.transcribe(audio_path, language="fr", fp16=False)
        return result["text"].strip()
    except Exception as e:
        st.error(f"Fallback transcription failed: {e}")
        return ""


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



# ============================================================
# AUTOMATIC FRENCH LIAISON ENGINE
# ============================================================

# Common h-muet words: liaison/elision is possible.
H_MUET_WORDS = {
    "habitude", "habitudes",
    "habiter", "habite", "habitent",
    "harmonie", "heure", "heures",
    "heureux", "heureuse",
    "histoire", "histoires",
    "hiver", "hivers",
    "homme", "hommes",
    "honneur", "honneurs",
    "hôpital", "hôpitaux",
    "hôtel", "hôtels",
    "humain", "humaine", "humains", "humaines",
    "humide",
    "hélicoptère", "hélicoptères",
}

# Common h-aspiré words: liaison is blocked.
H_ASPIRE_WORDS = {
    "haie", "haies",
    "haine",
    "hall", "halls",
    "hamac", "hamacs",
    "hamburger", "hamburgers",
    "hangar", "hangars",
    "harceler", "harcèlement",
    "haricot", "haricots",
    "harpe", "harpes",
    "hasard",
    "haut", "haute", "hauts", "hautes",
    "hauteur",
    "hérisson", "hérissons",
    "héros",
    "hibou", "hiboux",
    "homard", "homards",
    "honte",
    "hublot", "hublots",
    "hutte", "huttes",
}

# Words that behave like a disjunction and normally block liaison.
DISJUNCTION_WORDS = {
    "huit", "huitième", "huitièmes",
    "onze", "onzième", "onzièmes",
}


def starts_with_liaison_vowel(word: str) -> bool:
    """
    True when a word begins with a vowel sound or known h-muet
    and can therefore potentially trigger liaison.
    """
    word = clean_word(word)

    if not word:
        return False

    if word in DISJUNCTION_WORDS:
        return False

    if word in H_ASPIRE_WORDS:
        return False

    vowels = "aàâäæeéèêëiîïoôöœuùûüüyÿ"

    if word[0] in vowels:
        return True

    if word.startswith("h"):
        # Unknown h words are treated conservatively.
        return word in H_MUET_WORDS

    return False


# ------------------------------------------------------------
# Liaison trigger classes
# ------------------------------------------------------------

Z_LIAISON_WORDS = {
    # determiners
    "les", "des", "mes", "tes", "ses",
    "nos", "vos", "leurs",

    # pronouns / verbal forms
    "nous", "vous", "ils", "elles",

    # numerals
    "deux", "trois", "six", "dix",

    # frequent modifiers / prepositions / adverbs
    "très", "plus", "moins",
    "sans", "dans", "chez",
}

N_LIAISON_WORDS = {
    "un", "mon", "ton", "son",
    "on", "bon", "bien", "en",
}

T_LIAISON_WORDS = {
    "petit", "tout",
    "quand",
    "comment",
}

# Orthographic d commonly surfaces as liaison /t/.
D_TO_T_LIAISON_WORDS = {
    "grand",
}

# Special mutation in frequent expressions such as neuf ans.
F_TO_V_LIAISON_WORDS = {
    "neuf",
}


def liaison_sound_for_word(word: str) -> str:
    """
    Determine the normal liaison consonant associated with the
    first word of a potential liaison pair.
    """
    w = clean_word(word)

    if not w:
        return ""

    if w in Z_LIAISON_WORDS:
        return "z"

    if w in N_LIAISON_WORDS:
        return "n"

    if w in T_LIAISON_WORDS:
        return "t"

    if w in D_TO_T_LIAISON_WORDS:
        return "t"

    if w in F_TO_V_LIAISON_WORDS:
        return "v"

    # Productive plural/adjectival endings.
    if w.endswith(("s", "x", "z")):
        return "z"

    # Conservative t/d mapping for selected grammatical environments.
    if w.endswith(("t", "d")):
        return "t"

    return ""


def liaison_type_for_pair(w1: str, w2: str) -> str:
    """
    Pedagogical classification of the liaison environment.
    """
    a = clean_word(w1)
    b = clean_word(w2)

    if not a or not b:
        return "none"

    # Never after coordinating et.
    if a == "et":
        return "interdite"

    if b in H_ASPIRE_WORDS or b in DISJUNCTION_WORDS:
        return "interdite"

    # Determiner/pronoun + vowel-initial word
    if a in {
        "les", "des", "mes", "tes", "ses", "nos", "vos", "leurs",
        "un", "mon", "ton", "son",
        "nous", "vous", "ils", "elles", "on",
    }:
        return "obligatoire"

    # Common numeral contexts
    if a in {"deux", "trois", "six", "dix"}:
        return "obligatoire"

    # Prenominal adjective patterns
    if a in {
        "petit", "petits",
        "grand", "grands",
        "bon", "bons",
    }:
        return "obligatoire"

    # Fixed/highly productive interrogative connections
    if a in {"comment", "quand"}:
        return "obligatoire"

    # Adverb/preposition contexts are often stylistically variable.
    if a in {
        "très", "plus", "moins",
        "sans", "dans", "chez",
        "bien", "en",
    }:
        return "attendue"

    return "possible"


def _strip_ipa(ipa: str) -> str:
    ipa = str(ipa or "").strip()
    return ipa.strip("/[] ")


def build_connected_ipa(w1: str, w2: str, liaison_sound: str) -> str:
    """
    Generate a pedagogical connected IPA representation automatically.
    """
    ipa1 = _strip_ipa(get_ipa(w1))
    ipa2 = _strip_ipa(get_ipa(w2))

    if (
        not ipa1
        or not ipa2
        or ipa1 == "IPA unavailable"
        or ipa2 == "IPA unavailable"
    ):
        return "Connected pronunciation target"

    # Do not duplicate a consonant if phonemizer already supplied it.
    if liaison_sound and ipa1.endswith(liaison_sound):
        return f"/{ipa1}‿{ipa2}/"

    if liaison_sound:
        return f"/{ipa1}.{liaison_sound}‿{ipa2}/"

    return f"/{ipa1}‿{ipa2}/"


def liaison_explanation(w1: str, w2: str, sound: str, status: str) -> str:
    """
    Generate a learner-friendly explanation for the detected liaison.
    """
    if status == "obligatoire":
        intro = "This is an expected liaison in standard connected French."
    elif status == "attendue":
        intro = (
            "This liaison is common in careful connected speech, "
            "although usage may vary with speaking style."
        )
    else:
        intro = (
            "This boundary can permit liaison depending on grammatical "
            "and stylistic context."
        )

    return (
        f"{intro} The normally non-syllabified final consonant of "
        f"'{w1}' is realized as /{sound}/ and connects to the initial "
        f"vowel of '{w2}'."
    )


def detect_liaison_candidates(text: str):
    """
    Automatically detect French liaison targets in arbitrary text.

    The detector:
      • finds vowel-initial and h-muet environments;
      • blocks h-aspiré and disjunction environments;
      • determines the expected liaison consonant;
      • classifies the liaison pedagogically;
      • generates connected IPA automatically.
    """
    if not text:
        return []

    words = text.split()
    candidates = []

    for i in range(len(words) - 1):
        w1 = clean_word(words[i])
        w2 = clean_word(words[i + 1])

        if not w1 or not w2:
            continue

        # Explicitly show forbidden environments only when pedagogically useful.
        if w1 == "et":
            continue

        if not starts_with_liaison_vowel(w2):
            continue

        status = liaison_type_for_pair(w1, w2)

        if status == "interdite":
            continue

        sound = liaison_sound_for_word(w1)

        if not sound:
            continue

        phrase = f"{w1} {w2}"

        connected_ipa = build_connected_ipa(
            w1,
            w2,
            sound,
        )

        candidates.append({
            "phrase": phrase,
            "connected_ipa": connected_ipa,
            "focus_sound": f"{sound}‿",
            "liaison_sound": sound,
            "liaison_type": status,
            "explanation": liaison_explanation(
                w1,
                w2,
                sound,
                status,
            ),
            "tip": (
                f"Say '{w1}' and immediately attach /{sound}/ "
                f"to the beginning of '{w2}' without inserting a pause."
            ),
            "automatic": True,
        })

    # Remove duplicates.
    unique = []
    seen = set()

    for item in candidates:
        key = item["phrase"].lower()

        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique




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


# ===== COMPLETE SPEECH + IPA ANALYSIS =====

def phonetic_transcription(text: str) -> str:
    """
    Return a broad French IPA transcription of text.

    This is a canonical transcription generated from the recognized
    or target text; it is not a narrow manual transcription of every
    phonetic realization in the recording.
    """
    if text is None or not str(text).strip():
        return ""

    if not PHONEMIZER_AVAILABLE:
        return "IPA unavailable"

    try:
        ipa = phonemize(
            str(text).strip(),
            language="fr-fr",
            backend="espeak",
            strip=True,
            preserve_punctuation=True,
        )
        return str(ipa).strip() or "IPA unavailable"
    except Exception:
        try:
            ipa = phonemize(
                str(text).strip(),
                language="fr-fr",
                backend="espeak",
                strip=True,
            )
            return str(ipa).strip() or "IPA unavailable"
        except Exception:
            return "IPA unavailable"


def _estimate_french_syllables(text: str) -> int:
    """Approximate French syllable count from vowel-group nuclei."""
    if not text:
        return 0

    words = re.findall(
        r"[A-Za-zÀ-ÖØ-öø-ÿŒœÆæ'-]+",
        str(text).lower()
    )

    total = 0
    vowel_pattern = re.compile(
        r"[aeiouyàâäæéèêëîïôöœùûüÿ]+",
        re.IGNORECASE,
    )

    for word in words:
        groups = vowel_pattern.findall(word)
        total += max(1, len(groups)) if word else 0

    return total


def analyze_speech_acoustics(audio_path: str, transcript: str = "") -> dict:
    """
    Exploratory acoustic/prosodic analysis using Praat-Parselmouth.
    """
    result = {
        "duration_s": None,
        "f0_mean_hz": None,
        "f0_min_hz": None,
        "f0_max_hz": None,
        "f0_range_hz": None,
        "intensity_mean_db": None,
        "f1_median_hz": None,
        "f2_median_hz": None,
        "final_f0_hz": None,
        "final_pitch_change_hz": None,
        "final_pitch_slope_hz_s": None,
        "final_pitch_direction": "Unavailable",
        "word_count": 0,
        "syllable_count_est": 0,
        "speech_rate_syll_s": None,
    }

    try:
        import math
        import statistics
        import parselmouth

        sound = parselmouth.Sound(audio_path)
        duration = float(sound.get_total_duration())
        result["duration_s"] = duration

        # ---------------- F0 ----------------
        pitch = sound.to_pitch(
            time_step=0.01,
            pitch_floor=75,
            pitch_ceiling=500,
        )

        frequencies = list(pitch.selected_array["frequency"])
        times = list(pitch.xs())

        voiced_pairs = [
            (float(t), float(f))
            for t, f in zip(times, frequencies)
            if f and float(f) > 0 and math.isfinite(float(f))
        ]

        voiced_f0 = [f for _, f in voiced_pairs]

        if voiced_f0:
            result["f0_mean_hz"] = statistics.mean(voiced_f0)
            result["f0_min_hz"] = min(voiced_f0)
            result["f0_max_hz"] = max(voiced_f0)
            result["f0_range_hz"] = (
                result["f0_max_hz"] - result["f0_min_hz"]
            )
            result["final_f0_hz"] = voiced_f0[-1]

            # Final 20% pitch movement
            final_start = max(0.0, duration * 0.80)
            final_pairs = [
                (t, f)
                for t, f in voiced_pairs
                if t >= final_start
            ]

            if len(final_pairs) >= 2:
                t1, f1 = final_pairs[0]
                t2, f2 = final_pairs[-1]

                change = f2 - f1
                result["final_pitch_change_hz"] = change

                if t2 > t1:
                    result["final_pitch_slope_hz_s"] = change / (t2 - t1)

                if change > 5:
                    result["final_pitch_direction"] = "Rise"
                elif change < -5:
                    result["final_pitch_direction"] = "Fall"
                else:
                    result["final_pitch_direction"] = "Level"

        # ---------------- Intensity ----------------
        intensity = sound.to_intensity()
        intensity_values = [
            float(v)
            for v in intensity.values[0]
            if math.isfinite(float(v))
        ]

        if intensity_values:
            result["intensity_mean_db"] = statistics.mean(
                intensity_values
            )

        # ---------------- Formants ----------------
        formant = sound.to_formant_burg(
            time_step=0.01,
            max_number_of_formants=5,
            maximum_formant=5500,
        )

        f1_values = []
        f2_values = []

        if duration > 0:
            # Sample across the utterance while avoiding exact boundaries.
            for i in range(1, 30):
                t = duration * (i / 30.0)

                try:
                    f1 = formant.get_value_at_time(1, t)
                    f2 = formant.get_value_at_time(2, t)

                    if f1 and math.isfinite(float(f1)):
                        f1_values.append(float(f1))

                    if f2 and math.isfinite(float(f2)):
                        f2_values.append(float(f2))
                except Exception:
                    pass

        if f1_values:
            result["f1_median_hz"] = statistics.median(f1_values)

        if f2_values:
            result["f2_median_hz"] = statistics.median(f2_values)

        # ---------------- Speech rate ----------------
        words = len((transcript or "").split())
        syllables = _estimate_french_syllables(transcript)

        result["word_count"] = words
        result["syllable_count_est"] = syllables

        if duration > 0 and syllables:
            result["speech_rate_syll_s"] = syllables / duration

    except Exception as exc:
        result["analysis_error"] = str(exc)

    return result
