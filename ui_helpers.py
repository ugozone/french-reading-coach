import html
import tempfile
import streamlit as st
from gtts import gTTS

from speech import get_ipa, highlight_liaison_phrases if False else None
from speech import word_feedback, pronunciation_score, transcribe_audio_file, generate_coaching_message
from speech import get_ipa, clean_word
from db import save_phrase_attempt_to_db


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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
            tmp_wav.write(audio_file.read())
            wav_path = tmp_wav.name

        transcript = transcribe_audio_file(wav_path)

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
            "timestamp": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    current_lesson_id,
    phrase_history_key: str,
    max_phrase_attempts: int,
    enable_phrase_recording: bool = False
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

        with st.expander(f"Focus phrase: {phrase}", expanded=False):
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

            play_phrase_audio(
                phrase,
                key_suffix=f"{context}_{idx}_{clean_word(phrase)}",
                label=f"🔊 Hear only: {phrase}"
            )

            if enable_phrase_recording:
                st.caption("Practice this connected phrase separately before reading the whole sentence again.")

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
                            st.session_state[phrase_history_key].append({
                                "context": context,
                                "reference_text": text,
                                "phrase_result": phrase_result
                            })
                            st.session_state[phrase_history_key] = st.session_state[phrase_history_key][-max_phrase_attempts:]
