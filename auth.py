
import os
import streamlit as st
from supabase import create_client, Client
import requests


def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets[name]).strip()
    except Exception:
        return str(os.getenv(name, default)).strip()


SUPABASE_URL = get_secret("SUPABASE_URL", "")
SUPABASE_KEY = get_secret("SUPABASE_KEY", get_secret("SUPABASE_ANON_KEY", ""))


def get_supabase() -> Client | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.sidebar.error(f"Client creation failed: {e}")
        return None


supabase = get_supabase()


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


def get_current_user_id():
    user = get_current_user()
    return user.id if user else None


def get_current_user_email():
    user = get_current_user()
    if user and hasattr(user, "email"):
        return user.email
    return None


def render_auth_sidebar():
    st.sidebar.header("👤 Account")
    st.sidebar.write("Supabase URL:", SUPABASE_URL)
    st.sidebar.write("Has Supabase key:", bool(SUPABASE_KEY))
    st.sidebar.write("Client created:", bool(supabase))

    try:
        r = requests.get(SUPABASE_URL, timeout=10)
        st.sidebar.write("Host test status:", r.status_code)
    except Exception as e:
        st.sidebar.write("Host test failed:", str(e))

    auth_mode = st.sidebar.radio("Choose", ["Sign In", "Sign Up"])

    if auth_mode == "Sign Up":
        signup_name = st.sidebar.text_input("Full name")
        signup_email = st.sidebar.text_input("Email", key="signup_email")
        signup_password = st.sidebar.text_input("Password", type="password", key="signup_password")

        if st.sidebar.button("Create account"):
            try:
                if supabase is None:
                    st.sidebar.error("Supabase is not configured.")
                else:
                    supabase.auth.sign_up({
                        "email": signup_email,
                        "password": signup_password,
                        "options": {"data": {"full_name": signup_name}},
                    })
                    st.sidebar.success("Account created. Now sign in.")
            except Exception as e:
                st.sidebar.error(f"Sign up failed: {e}")

    else:
        signin_email = st.sidebar.text_input("Email", key="signin_email")
        signin_password = st.sidebar.text_input("Password", type="password", key="signin_password")

        if st.sidebar.button("Sign in"):
            try:
                if supabase is None:
                    st.sidebar.error("Supabase is not configured.")
                else:
                    supabase.auth.sign_in_with_password({
                        "email": signin_email,
                        "password": signin_password,
                    })
                    st.sidebar.success("Signed in successfully")
                    st.rerun()
            except Exception as e:
                st.sidebar.error(f"Sign in failed: {e}")

    current_user = get_current_user()

    if current_user:
        st.sidebar.success(f"Logged in as {current_user.email}")
        if st.sidebar.button("Sign out"):
            sign_out_user()
            st.rerun()
    else:
        st.warning("Please sign in to save and track progress.")
        st.stop()
