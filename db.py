from auth import supabase
from teacher_texts import TEACHER_TEXTS


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


def get_progress_rows(user_id: str):
    if supabase is None or user_id is None:
        return []

    try:
        result = (
            supabase.table("progress_summary")
            .select("best_score, average_score, attempt_count, last_practiced_at, lesson_id")
            .eq("user_id", user_id)
            .execute()
        )
        return result.data or []
    except Exception:
        return []
