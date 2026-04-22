import os
from typing import Optional

import requests
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


def render_auth_sidebar() -> None:
    """Render sign in / sign up controls in the sidebar."""
    st.sidebar.header("👤 Account")

    with st.sidebar.expander("Connection debug", expanded=False):
        st.write("Supabase URL:", SUPABASE_URL if SUPABASE_URL else "Not set")
        st.write("Has Supabase key:", bool(SUPABASE_KEY))
        st.write("Client created:", bool(supabase))

        if SUPABASE_URL:
            try:
                r = requests.get(SUPABASE_URL, timeout=10)
                st.write("Host test status:", r.status_code)
            except Exception as e:
                st.write("Host test failed:", str(e))

    current_user = get_current_user()

    if current_user:
        st.sidebar.success(f"Logged in as {getattr(current_user, 'email', 'Unknown user')}")
        if st.sidebar.button("Sign out"):
            sign_out_user()
            st.rerun()
        return

    auth_mode = st.sidebar.radio("Choose", ["Sign In", "Sign Up"])

    if auth_mode == "Sign Up":
        signup_name = st.sidebar.text_input("Full name", key="signup_name")
        signup_email = st.sidebar.text_input("Email", key="signup_email")
        signup_password = st.sidebar.text_input("Password", type="password", key="signup_password")

        if st.sidebar.button("Create account"):
            if supabase is None:
                st.sidebar.error("Supabase is not configured.")
                return

            if not signup_name or not signup_email or not signup_password:
                st.sidebar.error("Please fill in all fields.")
                return

            try:
                supabase.auth.sign_up(
                    {
                        "email": signup_email,
                        "password": signup_password,
                        "options": {
                            "data": {
                                "full_name": signup_name
                            }
                        },
                    }
                )
                st.sidebar.success("Account created. You can now sign in.")
            except Exception as e:
                st.sidebar.error(f"Sign up failed: {e}")

    else:
        signin_email = st.sidebar.text_input("Email", key="signin_email")
        signin_password = st.sidebar.text_input("Password", type="password", key="signin_password")

        if st.sidebar.button("Sign in"):
            if supabase is None:
                st.sidebar.error("Supabase is not configured.")
                return

            if not signin_email or not signin_password:
                st.sidebar.error("Please enter your email and password.")
                return

            try:
                supabase.auth.sign_in_with_password(
                    {
                        "email": signin_email,
                        "password": signin_password,
                    }
                )
                st.sidebar.success("Signed in successfully.")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Sign in failed: {e}")

    st.warning("Please sign in to save and track progress.")
    st.stop()
