# Admin Email Notification Setup

Every **new** teacher-access request is sent to:

**founder@intonasphereai.org**

The request is also stored in Supabase in `teacher_access_requests` with `status = pending`.

## Secure SMTP configuration

Do **not** put an email password in `auth.py` or commit it to GitHub.
Add the following values to your deployment's Streamlit secrets.

Example using a Gmail / Google Workspace sending account:

```toml
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USERNAME = "your-sending-account@gmail.com"
SMTP_PASSWORD = "YOUR_GOOGLE_APP_PASSWORD"
SMTP_FROM_EMAIL = "your-sending-account@gmail.com"
SMTP_FROM_NAME = "French Reading Coach"
SMTP_USE_SSL = "false"
SMTP_USE_STARTTLS = "true"
```

For Gmail/Google Workspace, `SMTP_PASSWORD` should be a Google **App Password**, not the normal Google account password. Two-step verification must normally be enabled to create an App Password.

If you use another SMTP provider, replace the host, port, username, password, and TLS/SSL settings with that provider's values.

## Streamlit Community Cloud

Open the deployed app → **Settings** → **Secrets**, then add the SMTP values above together with your existing `SUPABASE_URL` and `SUPABASE_KEY`/`SUPABASE_ANON_KEY` values. Reboot/redeploy the app after saving secrets.

## What the administrator receives

The email subject is:

`New Teacher Access Request: <teacher name>`

The email includes:
- teacher name;
- teacher email;
- school/institution;
- request message;
- confirmation that the request is pending in Supabase.

The teacher's submitted email is also set as `Reply-To`, so replying to the notification addresses the requesting teacher.

## Failure behavior

The Supabase request is saved first. The app then attempts the email notification. If SMTP is temporarily unavailable or not configured, the request remains safely stored in Supabase and the requester is told that email delivery was unsuccessful.
