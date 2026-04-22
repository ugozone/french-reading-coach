from datetime import datetime, timezone

from auth import supabase
from teacher_texts import TEACHER_TEXTS


GRAMMAR_LESSONS = [
    {
        "lesson_key": "a1_negation_ne_pas",
        "cefr_level": "A1",
        "topic": "Negation",
        "title": "Negation with ne ... pas",
        "explanation": "In French, basic negation usually wraps around the verb: ne + verb + pas. Example: Je parle -> Je ne parle pas.",
        "difficulty": 1,
    },
    {
        "lesson_key": "a1_articles_basics",
        "cefr_level": "A1",
        "topic": "Articles",
        "title": "French Articles: le / la / les / un / une / des",
        "explanation": "French uses definite articles (le, la, les) for specific nouns and indefinite articles (un, une, des) for non-specific nouns. Before a vowel, le/la become l’.",
        "difficulty": 1,
    },
    {
        "lesson_key": "a1_present_tense_er_verbs",
        "cefr_level": "A1",
        "topic": "Present Tense",
        "title": "Present tense: regular -ER verbs",
        "explanation": "Most regular French -ER verbs follow a pattern: je parle, tu parles, il/elle parle, nous parlons, vous parlez, ils/elles parlent.",
        "difficulty": 2,
    },
]

GRAMMAR_QUESTIONS = {
    "a1_negation_ne_pas": [
        {
            "question_order": 1,
            "question_type": "multiple_choice",
            "prompt": "Choose the correct negative sentence:",
            "options": ["Je parle pas français.", "Je ne parle pas français.", "Je pas parle français."],
            "correct_answer": "Je ne parle pas français.",
            "explanation": "In simple negation, ne comes before the verb and pas comes after it.",
            "target_sentence": "Je ne parle pas français.",
            "xp_value": 10,
        },
        {
            "question_order": 2,
            "question_type": "unscramble",
            "prompt": "Unscramble these words into a correct sentence:",
            "options": ["pas", "ne", "mange", "il"],
            "correct_answer": "Il ne mange pas.",
            "explanation": "The correct order is subject + ne + verb + pas.",
            "target_sentence": "Il ne mange pas.",
            "xp_value": 10,
        },
        {
            "question_order": 3,
            "question_type": "error_correction",
            "prompt": "Correct this sentence: Je parle ne pas anglais.",
            "options": None,
            "correct_answer": "Je ne parle pas anglais.",
            "explanation": "Ne goes before the verb and pas goes after the verb.",
            "target_sentence": "Je ne parle pas anglais.",
            "xp_value": 15,
        },
        {
            "question_order": 4,
            "question_type": "multiple_choice",
            "prompt": "Which sentence is correct?",
            "options": ["Nous ne aimons pas le café.", "Nous n’aimons pas le café.", "Nous pas aimons le café."],
            "correct_answer": "Nous n’aimons pas le café.",
            "explanation": "Before a vowel sound, ne usually becomes n’.",
            "target_sentence": "Nous n’aimons pas le café.",
            "xp_value": 15,
        },
        {
            "question_order": 5,
            "question_type": "build_sentence",
            "prompt": "Build a negative sentence with: Elle / regarder la télévision",
            "options": None,
            "correct_answer": "Elle ne regarde pas la télévision.",
            "explanation": "Use ne before the verb and pas after the verb.",
            "target_sentence": "Elle ne regarde pas la télévision.",
            "xp_value": 20,
        },
    ],
    "a1_articles_basics": [
        {
            "question_order": 1,
            "question_type": "multiple_choice",
            "prompt": "Choose the correct sentence:",
            "options": ["Je mange le pomme.", "Je mange une pomme.", "Je mange la pomme."],
            "correct_answer": "Je mange une pomme.",
            "explanation": "Use une for a non-specific feminine noun.",
            "target_sentence": "Je mange une pomme.",
            "xp_value": 10,
        },
        {
            "question_order": 2,
            "question_type": "multiple_choice",
            "prompt": "Which article is correct for 'livre'?",
            "options": ["la livre", "le livre", "une livre"],
            "correct_answer": "le livre",
            "explanation": "Livre is masculine.",
            "target_sentence": "Le livre est intéressant.",
            "xp_value": 10,
        },
        {
            "question_order": 3,
            "question_type": "multiple_choice",
            "prompt": "Choose the correct plural form:",
            "options": ["les chien", "les chiens", "le chiens"],
            "correct_answer": "les chiens",
            "explanation": "Plural nouns take les for definite articles.",
            "target_sentence": "Les chiens sont gentils.",
            "xp_value": 10,
        },
        {
            "question_order": 4,
            "question_type": "fill_blank",
            "prompt": "Complete: ___ école est grande.",
            "options": ["le", "la", "l’"],
            "correct_answer": "l’école",
            "explanation": "Before a vowel sound, le or la becomes l’.",
            "target_sentence": "L’école est grande.",
            "xp_value": 15,
        },
        {
            "question_order": 5,
            "question_type": "error_correction",
            "prompt": "Correct this: Je vois le voiture.",
            "options": None,
            "correct_answer": "Je vois la voiture.",
            "explanation": "Voiture is feminine, so it takes la.",
            "target_sentence": "Je vois la voiture.",
            "xp_value": 15,
        },
        {
            "question_order": 6,
            "question_type": "build_sentence",
            "prompt": "Build a sentence: (avoir) / un chien",
            "options": None,
            "correct_answer": "J’ai un chien.",
            "explanation": "Use un for masculine singular nouns.",
            "target_sentence": "J’ai un chien.",
            "xp_value": 20,
        },
    ],
    "a1_present_tense_er_verbs": [
        {
            "question_order": 1,
            "question_type": "multiple_choice",
            "prompt": "Choose the correct form: Je ___ français.",
            "options": ["parle", "parles", "parlons"],
            "correct_answer": "parle",
            "explanation": "For je with a regular -ER verb, the ending is usually -e.",
            "target_sentence": "Je parle français.",
            "xp_value": 10,
        },
        {
            "question_order": 2,
            "question_type": "multiple_choice",
            "prompt": "Choose the correct form: Nous ___ à la maison.",
            "options": ["parlez", "parlons", "parlent"],
            "correct_answer": "parlons",
            "explanation": "For nous, regular -ER verbs take the ending -ons.",
            "target_sentence": "Nous parlons à la maison.",
            "xp_value": 10,
        },
        {
            "question_order": 3,
            "question_type": "multiple_choice",
            "prompt": "Choose the correct form: Vous ___ lentement.",
            "options": ["parlez", "parlons", "parle"],
            "correct_answer": "parlez",
            "explanation": "For vous, regular -ER verbs take the ending -ez.",
            "target_sentence": "Vous parlez lentement.",
            "xp_value": 10,
        },
        {
            "question_order": 4,
            "question_type": "fill_blank",
            "prompt": "Complete with the correct verb form: Ils ___ le français.",
            "options": ["parle", "parlent", "parlez"],
            "correct_answer": "parlent",
            "explanation": "For ils/elles, regular -ER verbs usually end in -ent.",
            "target_sentence": "Ils parlent le français.",
            "xp_value": 15,
        },
        {
            "question_order": 5,
            "question_type": "error_correction",
            "prompt": "Correct this sentence: Tu parlons anglais.",
            "options": None,
            "correct_answer": "Tu parles anglais.",
            "explanation": "For tu, the correct ending is -es.",
            "target_sentence": "Tu parles anglais.",
            "xp_value": 15,
        },
        {
            "question_order": 6,
            "question_type": "build_sentence",
            "prompt": "Build a sentence with: aimer / nous / le café",
            "options": None,
            "correct_answer": "Nous aimons le café.",
            "explanation": "Remove -er from aimer, then add -ons for nous.",
            "target_sentence": "Nous aimons le café.",
            "xp_value": 20,
        },
    ],
}

GUIDED_READING_TASKS = [
    {
        "task_key": "a1_ma_journee",
        "title": "A1 Guided Reading: Ma journée",
        "cefr_level": "A1",
        "theme": "Daily Life",
        "full_text": (
            "Je m’appelle Paul. J’habite à Lyon. "
            "Le matin, je prends un café et je vais à l’école. "
            "Le soir, je regarde la télévision avec ma famille."
        ),
    }
]

GUIDED_READING_SECTIONS = {
    "a1_ma_journee": [
        {
            "section_order": 1,
            "section_text": "Je m’appelle Paul. J’habite à Lyon.",
            "comprehension_question": "Comment s’appelle-t-il ?",
            "comprehension_answer": "Paul",
            "vocab_question": "Dans quelle ville habite-t-il ?",
            "vocab_answer": "Lyon",
        },
        {
            "section_order": 2,
            "section_text": "Le matin, je prends un café et je vais à l’école.",
            "comprehension_question": "Que fait-il le matin ?",
            "comprehension_answer": "Il prend un café et il va à l’école.",
            "vocab_question": "Que veut dire 'le matin' ?",
            "vocab_answer": "In the morning",
        },
        {
            "section_order": 3,
            "section_text": "Le soir, je regarde la télévision avec ma famille.",
            "comprehension_question": "Que fait-il le soir ?",
            "comprehension_answer": "Il regarde la télévision avec sa famille.",
            "vocab_question": "Que veut dire 'le soir' ?",
            "vocab_answer": "In the evening",
        },
    ]
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def lesson_key_from_text(text_data: dict) -> str:
    title = text_data.get("title", "").strip().lower().replace(" ", "_")
    level = text_data.get("level", "").strip().lower()
    return f"{level}__{title}"


def ensure_lessons_seeded():
    if supabase is None:
        return

    rows = []
    for item in TEACHER_TEXTS:
        rows.append(
            {
                "lesson_key": lesson_key_from_text(item),
                "title": item.get("title", ""),
                "unit": item.get("unit", ""),
                "theme": item.get("theme", ""),
                "level": item.get("level", ""),
                "focus": item.get("focus", ""),
                "grammar_focus": item.get("grammar_focus", ""),
                "text_content": item.get("text", ""),
                "teacher_tip": item.get("teacher_tip", ""),
            }
        )

    try:
        supabase.table("lessons").upsert(rows, on_conflict="lesson_key").execute()
    except Exception:
        pass


def ensure_grammar_seeded():
    if supabase is None:
        return

    try:
        supabase.table("grammar_lessons").upsert(GRAMMAR_LESSONS, on_conflict="lesson_key").execute()
    except Exception:
        return

    try:
        lesson_result = supabase.table("grammar_lessons").select("id, lesson_key").execute()
        lesson_map = {row["lesson_key"]: row["id"] for row in (lesson_result.data or [])}
    except Exception:
        return

    for lesson_key, questions in GRAMMAR_QUESTIONS.items():
        lesson_id = lesson_map.get(lesson_key)
        if not lesson_id:
            continue

        try:
            existing = (
                supabase.table("grammar_questions")
                .select("id")
                .eq("lesson_id", lesson_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue

            rows = []
            for q in questions:
                rows.append(
                    {
                        "lesson_id": lesson_id,
                        "question_order": q["question_order"],
                        "question_type": q["question_type"],
                        "prompt": q["prompt"],
                        "options": q["options"],
                        "correct_answer": q["correct_answer"],
                        "explanation": q["explanation"],
                        "target_sentence": q["target_sentence"],
                        "xp_value": q["xp_value"],
                    }
                )

            supabase.table("grammar_questions").insert(rows).execute()
        except Exception:
            pass


def ensure_guided_reading_seeded():
    if supabase is None:
        return

    try:
        supabase.table("guided_reading_tasks").upsert(
            GUIDED_READING_TASKS,
            on_conflict="task_key",
        ).execute()
    except Exception:
        return

    try:
        task_result = supabase.table("guided_reading_tasks").select("id, task_key").execute()
        task_map = {row["task_key"]: row["id"] for row in (task_result.data or [])}
    except Exception:
        return

    for task_key, sections in GUIDED_READING_SECTIONS.items():
        task_id = task_map.get(task_key)
        if not task_id:
            continue

        try:
            existing = (
                supabase.table("guided_reading_sections")
                .select("id")
                .eq("task_id", task_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue

            rows = []
            for section in sections:
                rows.append(
                    {
                        "task_id": task_id,
                        "section_order": section["section_order"],
                        "section_text": section["section_text"],
                        "comprehension_question": section["comprehension_question"],
                        "comprehension_answer": section["comprehension_answer"],
                        "vocab_question": section["vocab_question"],
                        "vocab_answer": section["vocab_answer"],
                    }
                )

            supabase.table("guided_reading_sections").insert(rows).execute()
        except Exception:
            pass


def ensure_all_seeded():
    ensure_lessons_seeded()
    ensure_grammar_seeded()
    ensure_guided_reading_seeded()


def create_or_get_student(full_name: str, email: str, phone: str, level: str, class_name: str, teacher_name: str, notes: str):
    if supabase is None:
        return None, "Database not configured."

    email_clean = (email or "").strip().lower()
    full_name_clean = (full_name or "").strip()

    try:
        if email_clean:
            existing = (
                supabase.table("students")
                .select("*")
                .eq("email", email_clean)
                .limit(1)
                .execute()
            )
            if existing.data:
                return existing.data[0], "Existing profile loaded."

        existing_name = (
            supabase.table("students")
            .select("*")
            .eq("full_name", full_name_clean)
            .limit(1)
            .execute()
        )
        if existing_name.data:
            return existing_name.data[0], "Existing profile loaded."

        result = supabase.table("students").insert(
            {
                "full_name": full_name_clean,
                "email": email_clean if email_clean else None,
                "phone": (phone or "").strip() or None,
                "level": (level or "").strip() or None,
                "class_name": (class_name or "").strip() or None,
                "teacher_name": (teacher_name or "").strip() or None,
                "notes": (notes or "").strip() or None,
            }
        ).execute()

        if result.data:
            return result.data[0], "Profile created."
    except Exception as e:
        return None, str(e)

    return None, "Could not create or load student profile."


def find_student_by_email_or_name(full_name: str, email: str):
    if supabase is None:
        return None

    try:
        email_clean = (email or "").strip().lower()
        full_name_clean = (full_name or "").strip()

        if email_clean:
            result = (
                supabase.table("students")
                .select("*")
                .eq("email", email_clean)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]

        if full_name_clean:
            result = (
                supabase.table("students")
                .select("*")
                .eq("full_name", full_name_clean)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
    except Exception:
        return None

    return None


def get_student(student_id: str):
    if supabase is None or student_id is None:
        return None
    try:
        result = supabase.table("students").select("*").eq("id", student_id).limit(1).execute()
        if result.data:
            return result.data[0]
    except Exception:
        return None
    return None


def get_all_students():
    if supabase is None:
        return []
    try:
        result = supabase.table("students").select("*").order("created_at", desc=True).execute()
        return result.data or []
    except Exception:
        return []


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


def update_progress_summary(student_id: str, lesson_id):
    if supabase is None or lesson_id is None or student_id is None:
        return

    try:
        attempts = (
            supabase.table("attempts")
            .select("score, created_at")
            .eq("student_id", student_id)
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
                "student_id": student_id,
                "lesson_id": lesson_id,
                "best_score": best_score,
                "average_score": average_score,
                "attempt_count": attempt_count,
                "last_practiced_at": last_practiced_at,
            },
            on_conflict="student_id,lesson_id",
        ).execute()
    except Exception:
        pass


def save_attempt_to_db(student_id: str, lesson_id, attempt: dict):
    if supabase is None or student_id is None:
        return

    try:
        attempt_row = {
            "student_id": student_id,
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
            feedback_rows.append(
                {
                    "attempt_id": attempt_id,
                    "reference_word": item.get("reference", ""),
                    "spoken_word": item.get("spoken", ""),
                    "similarity": item.get("similarity", 0),
                    "status": item.get("status", ""),
                }
            )

        if feedback_rows:
            supabase.table("attempt_feedback").insert(feedback_rows).execute()

        update_progress_summary(student_id, lesson_id)
    except Exception:
        pass


def save_phrase_attempt_to_db(student_id: str, lesson_id, reference_text: str, phrase_result: dict):
    if supabase is None or student_id is None:
        return

    try:
        phrase_row = {
            "student_id": student_id,
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
            feedback_rows.append(
                {
                    "phrase_attempt_id": phrase_attempt_id,
                    "reference_word": item.get("reference", ""),
                    "spoken_word": item.get("spoken", ""),
                    "similarity": item.get("similarity", 0),
                    "status": item.get("status", ""),
                }
            )

        if feedback_rows:
            supabase.table("phrase_feedback").insert(feedback_rows).execute()

        update_progress_summary(student_id, lesson_id)
    except Exception:
        pass


def get_progress_rows(student_id: str):
    if supabase is None or student_id is None:
        return []

    try:
        result = (
            supabase.table("progress_summary")
            .select("best_score, average_score, attempt_count, last_practiced_at, lesson_id")
            .eq("student_id", student_id)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def get_attempt_history(student_id: str, limit: int = 10):
    if supabase is None or student_id is None:
        return []

    try:
        result = (
            supabase.table("attempts")
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        attempts = result.data or []
    except Exception:
        return []

    enriched = []
    for attempt in attempts:
        try:
            fb = (
                supabase.table("attempt_feedback")
                .select("*")
                .eq("attempt_id", attempt["id"])
                .execute()
            )
            attempt["feedback"] = fb.data or []
        except Exception:
            attempt["feedback"] = []
        enriched.append(attempt)

    return enriched


def get_phrase_history(student_id: str, limit: int = 10):
    if supabase is None or student_id is None:
        return []

    try:
        result = (
            supabase.table("phrase_attempts")
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        phrases = result.data or []
    except Exception:
        return []

    enriched = []
    for phrase in phrases:
        try:
            fb = (
                supabase.table("phrase_feedback")
                .select("*")
                .eq("phrase_attempt_id", phrase["id"])
                .execute()
            )
            phrase["feedback"] = fb.data or []
        except Exception:
            phrase["feedback"] = []
        enriched.append(phrase)

    return enriched


def get_grammar_lessons(level: str | None = None):
    if supabase is None:
        return []

    try:
        query = supabase.table("grammar_lessons").select("*").order("difficulty").order("title")
        if level:
            query = query.eq("cefr_level", level)
        result = query.execute()
        return result.data or []
    except Exception:
        return []


def get_grammar_questions(lesson_id: str):
    if supabase is None:
        return []

    try:
        result = (
            supabase.table("grammar_questions")
            .select("*")
            .eq("lesson_id", lesson_id)
            .order("question_order")
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def save_grammar_attempt(
    student_id: str,
    lesson_id: str,
    question_id: str,
    user_answer: str,
    is_correct: bool,
    xp_earned: int,
):
    if supabase is None or student_id is None:
        return

    try:
        supabase.table("grammar_attempts").insert(
            {
                "student_id": student_id,
                "lesson_id": lesson_id,
                "question_id": question_id,
                "user_answer": user_answer,
                "is_correct": is_correct,
                "xp_earned": xp_earned,
            }
        ).execute()
    except Exception:
        pass


def update_grammar_progress(student_id: str, lesson_id: str):
    if supabase is None or student_id is None:
        return

    try:
        attempts = (
            supabase.table("grammar_attempts")
            .select("is_correct, xp_earned, answered_at")
            .eq("student_id", student_id)
            .eq("lesson_id", lesson_id)
            .order("answered_at")
            .execute()
        )

        rows = attempts.data or []
        if not rows:
            return

        total_questions = len(rows)
        correct_answers = sum(1 for r in rows if r["is_correct"])
        total_xp = sum(int(r.get("xp_earned", 0)) for r in rows)

        streak_count = 0
        for row in reversed(rows):
            if row["is_correct"]:
                streak_count += 1
            else:
                break

        accuracy = correct_answers / total_questions if total_questions else 0
        if accuracy >= 0.9:
            mastery = "Master"
        elif accuracy >= 0.75:
            mastery = "Strong"
        elif accuracy >= 0.5:
            mastery = "Developing"
        else:
            mastery = "Starter"

        last_answered_at = rows[-1]["answered_at"]

        supabase.table("grammar_progress").upsert(
            {
                "student_id": student_id,
                "lesson_id": lesson_id,
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "total_xp": total_xp,
                "streak_count": streak_count,
                "mastery_level": mastery,
                "last_answered_at": last_answered_at,
            },
            on_conflict="student_id,lesson_id",
        ).execute()
    except Exception:
        pass


def get_grammar_progress(student_id: str, lesson_id: str):
    if supabase is None or student_id is None:
        return None

    try:
        result = (
            supabase.table("grammar_progress")
            .select("*")
            .eq("student_id", student_id)
            .eq("lesson_id", lesson_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception:
        pass
    return None


def get_grammar_attempt_summary(student_id: str, lesson_id: str):
    if supabase is None or student_id is None or lesson_id is None:
        return {"answered": 0, "correct": 0, "xp": 0}

    try:
        result = (
            supabase.table("grammar_attempts")
            .select("is_correct, xp_earned")
            .eq("student_id", student_id)
            .eq("lesson_id", lesson_id)
            .execute()
        )
        rows = result.data or []
        return {
            "answered": len(rows),
            "correct": sum(1 for r in rows if r.get("is_correct")),
            "xp": sum(int(r.get("xp_earned", 0)) for r in rows),
        }
    except Exception:
        return {"answered": 0, "correct": 0, "xp": 0}


def get_guided_reading_tasks(level: str | None = None):
    if supabase is None:
        return []

    try:
        query = supabase.table("guided_reading_tasks").select("*").order("title")
        if level:
            query = query.eq("cefr_level", level)
        result = query.execute()
        return result.data or []
    except Exception:
        return []


def get_guided_reading_sections(task_id: str):
    if supabase is None:
        return []

    try:
        result = (
            supabase.table("guided_reading_sections")
            .select("*")
            .eq("task_id", task_id)
            .order("section_order")
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def create_guided_reading_attempt(student_id: str, task_id: str):
    if supabase is None or student_id is None:
        return None

    try:
        existing = (
            supabase.table("guided_reading_attempts")
            .select("*")
            .eq("student_id", student_id)
            .eq("task_id", task_id)
            .eq("status", "in_progress")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]

        result = supabase.table("guided_reading_attempts").insert(
            {
                "student_id": student_id,
                "task_id": task_id,
                "status": "in_progress",
            }
        ).execute()

        if result.data:
            return result.data[0]
    except Exception:
        return None
    return None


def get_latest_in_progress_guided_attempt(student_id: str, task_id: str):
    if supabase is None or student_id is None:
        return None

    try:
        result = (
            supabase.table("guided_reading_attempts")
            .select("*")
            .eq("student_id", student_id)
            .eq("task_id", task_id)
            .eq("status", "in_progress")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception:
        pass
    return None


def normalize_simple(text: str) -> str:
    if text is None:
        return ""
    return " ".join(str(text).strip().lower().replace("’", "'").split())


def save_guided_section_attempt(
    attempt_id: str,
    section_id: str,
    recognized_text: str,
    pronunciation_score: float,
    comprehension_response: str,
    comprehension_correct: bool,
    vocab_response: str,
    vocab_correct: bool,
    coaching_message: str,
):
    if supabase is None:
        return

    try:
        existing = (
            supabase.table("guided_reading_section_attempts")
            .select("id")
            .eq("attempt_id", attempt_id)
            .eq("section_id", section_id)
            .limit(1)
            .execute()
        )

        payload = {
            "attempt_id": attempt_id,
            "section_id": section_id,
            "recognized_text": recognized_text,
            "pronunciation_score": pronunciation_score,
            "comprehension_response": comprehension_response,
            "comprehension_correct": comprehension_correct,
            "vocab_response": vocab_response,
            "vocab_correct": vocab_correct,
            "coaching_message": coaching_message,
        }

        if existing.data:
            row_id = existing.data[0]["id"]
            supabase.table("guided_reading_section_attempts").update(payload).eq("id", row_id).execute()
        else:
            supabase.table("guided_reading_section_attempts").insert(payload).execute()

    except Exception:
        pass


def get_guided_completed_section_count(attempt_id: str) -> int:
    if supabase is None or attempt_id is None:
        return 0

    try:
        result = (
            supabase.table("guided_reading_section_attempts")
            .select("id")
            .eq("attempt_id", attempt_id)
            .execute()
        )
        return len(result.data or [])
    except Exception:
        return 0


def finalize_guided_reading_attempt(attempt_id: str):
    if supabase is None:
        return

    try:
        section_result = (
            supabase.table("guided_reading_section_attempts")
            .select("*")
            .eq("attempt_id", attempt_id)
            .execute()
        )
        rows = section_result.data or []
        if not rows:
            return

        avg_pron = round(sum(float(r.get("pronunciation_score", 0)) for r in rows) / len(rows), 2)
        comp_correct = sum(1 for r in rows if r.get("comprehension_correct"))
        vocab_correct = sum(1 for r in rows if r.get("vocab_correct"))
        total_checks = len(rows) * 2
        comp_score = round(((comp_correct + vocab_correct) / total_checks) * 100, 2) if total_checks else 0
        total_score = round((avg_pron * 0.6) + (comp_score * 0.4), 2)

        supabase.table("guided_reading_attempts").update(
            {
                "status": "completed",
                "completed_at": _utc_now_iso(),
                "overall_pronunciation_score": avg_pron,
                "comprehension_score": comp_score,
                "total_score": total_score,
            }
        ).eq("id", attempt_id).execute()
    except Exception:
        pass


def get_guided_reading_attempt_status(student_id: str, task_id: str):
    if supabase is None or student_id is None:
        return None

    try:
        result = (
            supabase.table("guided_reading_attempts")
            .select("*")
            .eq("student_id", student_id)
            .eq("task_id", task_id)
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception:
        pass
    return None


def get_guided_reading_attempt_overview():
    if supabase is None:
        return []

    try:
        result = (
            supabase.table("guided_reading_attempts")
            .select(
                """
                id,
                student_id,
                task_id,
                status,
                started_at,
                completed_at,
                overall_pronunciation_score,
                comprehension_score,
                total_score,
                guided_reading_tasks(title, cefr_level, theme),
                students(full_name, email, class_name, teacher_name, level)
                """
            )
            .order("started_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def get_guided_reading_attempt_details(attempt_id: str):
    if supabase is None:
        return []

    try:
        result = (
            supabase.table("guided_reading_section_attempts")
            .select(
                """
                id,
                attempt_id,
                section_id,
                recognized_text,
                pronunciation_score,
                comprehension_response,
                comprehension_correct,
                vocab_response,
                vocab_correct,
                coaching_message,
                completed_at,
                guided_reading_sections(
                    section_order,
                    section_text,
                    comprehension_question,
                    comprehension_answer,
                    vocab_question,
                    vocab_answer
                )
                """
            )
            .eq("attempt_id", attempt_id)
            .order("completed_at")
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def is_teacher_name(name: str) -> bool:
    if supabase is None or not name:
        return False

    try:
        result = (
            supabase.table("teacher_access")
            .select("teacher_name, is_active")
            .eq("teacher_name", name.strip())
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception:
        return False


def assign_reading_task(
    teacher_name: str,
    student_id: str,
    task_id: str,
    due_date: str | None = None,
    notes: str = "",
):
    if supabase is None:
        return False, "Database is not available."

    try:
        payload = {
            "teacher_name": teacher_name.strip(),
            "student_id": student_id,
            "task_id": task_id,
            "due_date": due_date if due_date else None,
            "notes": notes.strip() or None,
            "status": "assigned",
        }
        supabase.table("reading_assignments").upsert(payload, on_conflict="student_id,task_id").execute()
        return True, "Assignment created successfully."
    except Exception as e:
        return False, str(e)


def get_assignments_for_student(student_id: str):
    if supabase is None or not student_id:
        return []

    try:
        result = (
            supabase.table("reading_assignments")
            .select(
                """
                id,
                teacher_name,
                student_id,
                assigned_at,
                due_date,
                status,
                notes,
                task_id,
                guided_reading_tasks(title, cefr_level, theme, full_text)
                """
            )
            .eq("student_id", student_id)
            .order("assigned_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def get_all_assignments_overview():
    if supabase is None:
        return []

    try:
        result = (
            supabase.table("reading_assignments")
            .select(
                """
                id,
                teacher_name,
                student_id,
                assigned_at,
                due_date,
                status,
                notes,
                task_id,
                guided_reading_tasks(title, cefr_level, theme),
                students(full_name, email, class_name, teacher_name, level)
                """
            )
            .order("assigned_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def mark_assignment_started(student_id: str, task_id: str):
    if supabase is None:
        return

    try:
        supabase.table("reading_assignments").update(
            {"status": "started"}
        ).eq("student_id", student_id).eq("task_id", task_id).eq("status", "assigned").execute()
    except Exception:
        pass


def mark_assignment_completed(student_id: str, task_id: str):
    if supabase is None:
        return

    try:
        supabase.table("reading_assignments").update(
            {"status": "completed"}
        ).eq("student_id", student_id).eq("task_id", task_id).execute()
    except Exception:
        pass
