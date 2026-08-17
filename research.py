import csv
import io
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import streamlit as st
from supabase import Client, create_client

from auth import get_secret, supabase


RESEARCH_CONSENT_VERSION = get_secret("RESEARCH_CONSENT_VERSION", "pilot-v1.0")
RESEARCH_MODE = get_secret("RESEARCH_MODE", "false").lower() in {"1", "true", "yes", "on"}
RESEARCH_APPROVAL_REFERENCE = get_secret("RESEARCH_APPROVAL_REFERENCE", "")
RESEARCH_CONSENT_TEXT = get_secret("RESEARCH_CONSENT_TEXT", "")
RESEARCH_ADMIN_EMAILS = {
    item.strip().lower()
    for item in get_secret("RESEARCH_ADMIN_EMAILS", "founder@intonasphereai.org").split(",")
    if item.strip()
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def research_enabled() -> bool:
    """Enable collection only when launch, approval, consent, and secure server write settings are present."""
    return bool(
        RESEARCH_MODE
        and RESEARCH_APPROVAL_REFERENCE
        and RESEARCH_CONSENT_TEXT
        and get_secret("SUPABASE_SERVICE_ROLE_KEY", "")
    )


def research_status() -> tuple[bool, str]:
    if not RESEARCH_MODE:
        return False, "Research data collection is OFF for this public beta."
    missing = []
    if not RESEARCH_APPROVAL_REFERENCE:
        missing.append("RESEARCH_APPROVAL_REFERENCE")
    if not RESEARCH_CONSENT_TEXT:
        missing.append("RESEARCH_CONSENT_TEXT")
    if not get_secret("SUPABASE_SERVICE_ROLE_KEY", ""):
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        return False, "Research collection is locked because required approved-study settings are missing: " + ", ".join(missing)
    return True, f"Research collection is active under approval/reference: {RESEARCH_APPROVAL_REFERENCE}"


def is_research_admin(email: Optional[str]) -> bool:
    return bool(email and email.strip().lower() in RESEARCH_ADMIN_EMAILS)


def _admin_client() -> Optional[Client]:
    """Create a server-side admin client only when a service-role secret is configured."""
    url = get_secret("SUPABASE_URL", "")
    service_key = get_secret("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not service_key:
        return None
    try:
        return create_client(url, service_key)
    except Exception:
        return None


def _safe_insert(table: str, payload: dict[str, Any]):
    # Research records are written server-side with the service role so the public
    # anon key never receives read/write access to the research tables. Operational
    # beta feedback may fall back to the anon client if its insert-only policy exists.
    client = _admin_client() if table.startswith("research_") else (_admin_client() or supabase)
    if client is None:
        return False, "Supabase secure storage is not configured."
    try:
        client.table(table).insert(payload).execute()
        return True, "Saved."
    except Exception as exc:
        text = str(exc).lower()
        if table in text or "relation" in text or "permission" in text:
            return False, f"{table} storage is not ready. Run PUBLIC_RESEARCH_BETA_SETUP.sql in Supabase."
        return False, "Could not save this item right now."


def enroll_participant(
    age_18_or_older: bool,
    consent_agreed: bool,
    french_level: str = "Prefer not to say",
    language_background: str = "Prefer not to say",
):
    """Create a pseudonymous research participant and session.

    No name, email, IP address, or raw audio is stored here. The participant and
    session UUIDs are generated in the app so public RLS does not need SELECT access.
    """
    if not research_enabled():
        return False, "Research enrollment is currently closed.", None
    if not age_18_or_older:
        return False, "This pilot research enrollment is currently limited to participants age 18 or older.", None
    if not consent_agreed:
        return False, "Please provide consent before joining the research pilot.", None

    participant_id = str(uuid.uuid4())
    participant_code = f"FR-{uuid.uuid4().hex[:8].upper()}"
    session_id = str(uuid.uuid4())

    participant_payload = {
        "id": participant_id,
        "participant_code": participant_code,
        "consent_version": RESEARCH_CONSENT_VERSION,
        "consent_given": True,
        "age_18_or_older": True,
        "french_level": french_level or "Prefer not to say",
        "language_background": language_background or "Prefer not to say",
        "enrolled_at": _utc_now_iso(),
    }
    ok, msg = _safe_insert("research_participants", participant_payload)
    if not ok:
        return False, msg, None

    session_payload = {
        "id": session_id,
        "participant_id": participant_id,
        "participant_code": participant_code,
        "consent_version": RESEARCH_CONSENT_VERSION,
        "started_at": _utc_now_iso(),
        "app_version": "public-research-beta-v1.0",
    }
    ok, msg = _safe_insert("research_sessions", session_payload)
    if not ok:
        return False, msg, None

    state = {
        "participant_id": participant_id,
        "participant_code": participant_code,
        "session_id": session_id,
    }
    st.session_state.research_participant = state
    log_research_event("research_enrollment", "research", {"consent_version": RESEARCH_CONSENT_VERSION})
    return True, "Research participation is active for this browser session.", state


def get_research_state() -> Optional[dict[str, str]]:
    state = st.session_state.get("research_participant")
    if not research_enabled() or not isinstance(state, dict):
        return None
    if not state.get("participant_id") or not state.get("session_id"):
        return None
    return state


def leave_research_session() -> None:
    """Stop collection for the current browser session without deleting prior consented data."""
    state = get_research_state()
    if state:
        log_research_event("research_session_left", "research", {})
    st.session_state.pop("research_participant", None)


def log_research_event(event_type: str, activity_type: str, metrics: Optional[dict[str, Any]] = None) -> bool:
    """Record a minimal event only for a currently consented participant.

    Callers should pass aggregate task measures, not names, email addresses, raw
    audio, pasted free text, or speech transcripts.
    """
    state = get_research_state()
    if not state:
        return False

    payload = {
        "id": str(uuid.uuid4()),
        "session_id": state["session_id"],
        "participant_id": state["participant_id"],
        "participant_code": state["participant_code"],
        "event_type": (event_type or "event")[:80],
        "activity_type": (activity_type or "app")[:80],
        "metrics": metrics or {},
        "created_at": _utc_now_iso(),
    }
    ok, _ = _safe_insert("research_events", payload)
    return ok


def submit_beta_feedback(rating: int, category: str, message: str):
    """Store operational beta feedback separately from the research dataset."""
    message_clean = (message or "").strip()
    if not message_clean:
        return False, "Please enter your feedback before submitting."

    rating_int = max(1, min(5, int(rating)))
    payload = {
        "id": str(uuid.uuid4()),
        "rating": rating_int,
        "category": (category or "General")[:60],
        "message": message_clean[:4000],
        "research_participant_code": (get_research_state() or {}).get("participant_code"),
        "created_at": _utc_now_iso(),
    }
    return _safe_insert("beta_feedback", payload)


def _fetch_admin_table(table: str, columns: str = "*"):
    client = _admin_client()
    if client is None:
        return None, "Research admin export requires SUPABASE_SERVICE_ROLE_KEY in Streamlit secrets."
    try:
        result = client.table(table).select(columns).order("created_at", desc=True).execute()
        return result.data or [], ""
    except Exception:
        # research_participants uses enrolled_at rather than created_at
        try:
            result = client.table(table).select(columns).execute()
            return result.data or [], ""
        except Exception:
            return None, f"Could not read {table}. Run PUBLIC_RESEARCH_BETA_SETUP.sql and check the service-role secret."


def get_research_admin_summary():
    participants, p_msg = _fetch_admin_table("research_participants")
    sessions, s_msg = _fetch_admin_table("research_sessions")
    events, e_msg = _fetch_admin_table("research_events")
    feedback, f_msg = _fetch_admin_table("beta_feedback")
    error = next((m for m in [p_msg, s_msg, e_msg, f_msg] if m), "")
    if error:
        return None, error
    return {
        "participants": participants,
        "sessions": sessions,
        "events": events,
        "feedback": feedback,
    }, ""


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    keys = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                keys.append(key)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        normalized = {}
        for key in keys:
            value = row.get(key)
            if isinstance(value, (dict, list)):
                import json
                value = json.dumps(value, ensure_ascii=False)
            normalized[key] = value
        writer.writerow(normalized)
    return buffer.getvalue()
