import os
import re
import smtplib
from email.message import EmailMessage
from typing import Optional

import streamlit as st
from supabase import Client, create_client


def get_secret(name: str, default: str = "") -> str:
    """Read from Streamlit secrets first, then environment variables."""
    try:
        value = st.secrets[name]
        return str(value).strip()
    except Exception:
        return str(os.getenv(name, default)).strip()


SUPABASE_URL = get_secret("SUPABASE_URL", "")
SUPABASE_KEY = get_secret("SUPABASE_KEY", get_secret("SUPABASE_ANON_KEY", ""))

# All new teacher-access requests notify this administrator address.
ADMIN_NOTIFICATION_EMAIL = "founder@intonasphereai.org"


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def send_teacher_request_email(full_name: str, email: str, institution: str = "", message: str = ""):
    """Send a new teacher-access request to the fixed administrator inbox.

    SMTP credentials are read only from Streamlit secrets/environment variables.
    No mail password is stored in source code.
    """
    smtp_host = get_secret("SMTP_HOST", "")
    smtp_port_raw = get_secret("SMTP_PORT", "587")
    smtp_username = get_secret("SMTP_USERNAME", "")
    smtp_password = get_secret("SMTP_PASSWORD", "")
    smtp_from_email = get_secret("SMTP_FROM_EMAIL", smtp_username)
    smtp_from_name = get_secret("SMTP_FROM_NAME", "French Reading Coach")
    smtp_use_ssl = _as_bool(get_secret("SMTP_USE_SSL", "false"), False)
    smtp_use_starttls = _as_bool(get_secret("SMTP_USE_STARTTLS", "true"), True)

    if not smtp_host or not smtp_username or not smtp_password or not smtp_from_email:
        return False, "Admin email notification is not configured yet."

    try:
        smtp_port = int(smtp_port_raw)
    except (TypeError, ValueError):
        smtp_port = 465 if smtp_use_ssl else 587

    mail = EmailMessage()
    mail["Subject"] = f"New Teacher Access Request: {full_name}"
    mail["From"] = f"{smtp_from_name} <{smtp_from_email}>"
    mail["To"] = ADMIN_NOTIFICATION_EMAIL
    mail["Reply-To"] = email
    mail.set_content(
        "A new teacher has requested access to the French Reading Coach.\n\n"
        f"Name: {full_name}\n"
        f"Email: {email}\n"
        f"School / Institution: {institution or 'Not provided'}\n"
        f"Message: {message or 'Not provided'}\n\n"
        "The request has also been saved in Supabase with status=pending.\n"
        "Review and approve the teacher from the administrator side before granting dashboard access.\n"
    )

    try:
        if smtp_use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(mail)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.ehlo()
                if smtp_use_starttls:
                    server.starttls()
                    server.ehlo()
                server.login(smtp_username, smtp_password)
                server.send_message(mail)
        return True, f"Administrator notified at {ADMIN_NOTIFICATION_EMAIL}."
    except Exception:
        return False, "The request was saved, but the administrator email could not be sent."


def get_supabase() -> Optional[Client]:
    """Create and return a Supabase client if credentials exist."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None


supabase = get_supabase()


def sign_out_user() -> None:
    """Sign out the current user."""
    if supabase is not None:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass


def get_current_user():
    """Return the currently signed-in user, or None."""
    if supabase is None:
        return None

    try:
        user_response = supabase.auth.get_user()
        return user_response.user
    except Exception:
        return None


def get_current_user_id() -> Optional[str]:
    """Return the current user's ID."""
    user = get_current_user()
    return getattr(user, "id", None) if user else None


def get_current_user_email() -> Optional[str]:
    """Return the current user's email."""
    user = get_current_user()
    return getattr(user, "email", None) if user else None


def submit_teacher_access_request(full_name: str, email: str, institution: str = "", message: str = ""):
    """
    Submit a teacher-access request to a separate pending-request table.

    This intentionally does NOT write to teacher_access. Approval must be
    performed by an administrator in Supabase.
    """
    if supabase is None:
        return False, "Teacher access requests are not configured yet."

    full_name_clean = (full_name or "").strip()
    email_clean = (email or "").strip().lower()
    institution_clean = (institution or "").strip()
    message_clean = (message or "").strip()

    if not full_name_clean:
        return False, "Please enter your full name."
    if not email_clean or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_clean):
        return False, "Please enter a valid email address."

    payload = {
        "full_name": full_name_clean,
        "email": email_clean,
        "institution": institution_clean or None,
        "message": message_clean or None,
        "status": "pending",
    }

    try:
        supabase.table("teacher_access_requests").insert(payload).execute()
        email_ok, email_msg = send_teacher_request_email(
            full_name_clean,
            email_clean,
            institution_clean,
            message_clean,
        )
        if email_ok:
            return True, (
                f"Request submitted and sent to {ADMIN_NOTIFICATION_EMAIL}. "
                "An administrator must approve your teacher access before you can open the dashboard."
            )
        return True, (
            "Request saved successfully in Supabase, but the administrator email notification could not be delivered. "
            "Please contact the administrator if your request is urgent."
        )
    except Exception as exc:
        error_text = str(exc).lower()
        if "duplicate" in error_text or "unique" in error_text or "23505" in error_text:
            return True, "A teacher-access request already exists for this email. Please wait for administrator review."
        if "teacher_access_requests" in error_text or "relation" in error_text or "permission" in error_text:
            return False, "Teacher request storage is not ready. The administrator needs to run TEACHER_ACCESS_SETUP.sql in Supabase."
        return False, "Could not submit the teacher-access request. Please contact the app administrator."



def render_teacher_invite_activation() -> bool:
    """
    Handle a Supabase teacher invitation using token_hash in the URL.

    Expected URL:
    ?token_hash=...&type=invite

    Returns True while the invitation activation interface is being shown.
    """
    try:
        token_hash = str(st.query_params.get("token_hash", "") or "").strip()
        invite_type = str(st.query_params.get("type", "") or "").strip().lower()
    except Exception:
        token_hash = ""
        invite_type = ""

    if not token_hash or invite_type != "invite":
        return False

    st.sidebar.header("🔐 Activate Teacher Account")
    st.sidebar.success("Teacher invitation detected.")
    st.sidebar.caption(
        "Create your password below. After activation, use the normal Teacher sign in panel."
    )

    with st.sidebar.form("teacher_invite_activation_form"):
        new_password = st.text_input(
            "Create password",
            type="password",
            key="teacher_invite_password",
        )
        confirm_password = st.text_input(
            "Confirm password",
            type="password",
            key="teacher_invite_password_confirm",
        )
        activate = st.form_submit_button("Activate Teacher Account")

    if activate:
        if supabase is None:
            st.sidebar.error("Supabase authentication is not configured.")
            return True

        if len(new_password or "") < 8:
            st.sidebar.error("Password must contain at least 8 characters.")
            return True

        if new_password != confirm_password:
            st.sidebar.error("The two passwords do not match.")
            return True

        try:
            # Verify the one-time Supabase invitation token.
            supabase.auth.verify_otp(
                {
                    "token_hash": token_hash,
                    "type": "invite",
                }
            )

            # The verified invitation creates an authenticated session,
            # allowing the invited user to choose a password.
            supabase.auth.update_user(
                {
                    "password": new_password,
                }
            )

            user = get_current_user()
            activated_email = (
                getattr(user, "email", "")
                if user is not None
                else ""
            )

            # Require a fresh normal login after activation.
            try:
                supabase.auth.sign_out()
            except Exception:
                pass

            st.session_state["teacher_activation_message"] = (
                f"Teacher account activated"
                + (f" for {activated_email}" if activated_email else "")
                + ". You can now sign in with your new password."
            )

            # Remove the one-time token from the browser URL.
            try:
                st.query_params.clear()
            except Exception:
                pass

            st.rerun()

        except Exception as exc:
            error_text = str(exc).lower()

            if (
                "expired" in error_text
                or "invalid" in error_text
                or "otp" in error_text
                or "token" in error_text
            ):
                st.sidebar.error(
                    "This invitation link is invalid or has expired. "
                    "Ask the administrator to send a new invitation."
                )
            else:
                st.sidebar.error(
                    "Teacher account activation could not be completed. "
                    "Please request a new invitation or contact the administrator."
                )

    return True


def render_auth_sidebar() -> None:
    """Render optional teacher sign-in and access-request controls."""

    activation_message = st.session_state.pop(
        "teacher_activation_message",
        "",
    )
    if activation_message:
        st.sidebar.success(activation_message)

    if render_teacher_invite_activation():
        return

    st.sidebar.header("👤 Account")

    current_user = get_current_user()

    if current_user:
        st.sidebar.success(f"Signed in as {getattr(current_user, 'email', 'Unknown user')}")
        st.sidebar.caption("Teacher dashboard access is granted only to administrator-approved teacher emails.")
        if st.sidebar.button("Sign out", key="account_sign_out"):
            sign_out_user()
            st.session_state.teacher_name = ""
            st.rerun()
        return

    st.sidebar.caption("Students do not need an account. Teacher accounts require administrator approval.")

    with st.sidebar.expander("Teacher sign in", expanded=False):
        signin_email = st.text_input("Approved teacher email", key="signin_email")
        signin_password = st.text_input("Password", type="password", key="signin_password")

        if st.button("Sign in", key="teacher_signin_btn"):
            if supabase is None:
                st.error("Teacher sign-in is not configured.")
                return

            if not signin_email or not signin_password:
                st.error("Please enter your email and password.")
                return

            try:
                supabase.auth.sign_in_with_password(
                    {
                        "email": signin_email.strip().lower(),
                        "password": signin_password,
                    }
                )
                st.success("Signed in successfully.")
                st.rerun()
            except Exception:
                st.error("Sign in failed. Check your approved email/password or contact the administrator.")

    with st.sidebar.expander("Request Teacher Access", expanded=False):
        st.caption(
            "Request access here. Submitting this form does not create a teacher account or grant dashboard access."
        )
        request_name = st.text_input("Full name", key="teacher_request_name")
        request_email = st.text_input("Email", key="teacher_request_email")
        request_institution = st.text_input("School / institution (optional)", key="teacher_request_institution")
        request_message = st.text_area(
            "Why do you need teacher access? (optional)",
            key="teacher_request_message",
            height=90,
        )

        if st.button("Submit access request", key="teacher_request_submit"):
            ok, msg = submit_teacher_access_request(
                request_name,
                request_email,
                request_institution,
                request_message,
            )
            if ok:
                st.success(msg)
            else:
                st.error(msg)
