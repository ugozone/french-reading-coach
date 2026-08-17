# Relaunch Checklist — French Reading Coach Public Beta

## A. Required before the free public relaunch

1. Push the project to GitHub without `.streamlit/secrets.toml`.
2. Deploy `app.py` to your Streamlit host.
3. Add `SUPABASE_URL` and `SUPABASE_ANON_KEY` in Streamlit Secrets.
4. Run `TEACHER_ACCESS_SETUP.sql` in Supabase if teacher requests are not already configured.
5. Run `PUBLIC_RESEARCH_BETA_SETUP.sql` in Supabase. This creates the research/feedback tables, but **does not turn research collection on**.
6. Configure the SMTP settings described in `EMAIL_NOTIFICATION_SETUP.md` so teacher requests notify `founder@intonasphereai.org`.
7. Keep `RESEARCH_MODE = "false"` for the public usability pilot unless/until the applicable research authorization is complete.
8. Open the public URL in an incognito/private browser and verify:
   - Pronunciation opens without student sign-up.
   - Grammar opens without student sign-up.
   - Guided Reading opens without student sign-up.
   - Teacher Dashboard remains protected.
   - Teacher access requests are stored and emailed to the admin address.
   - Beta feedback submits successfully.

## B. Required before activating research collection

1. Complete the applicable institutional review/IRB determination or approval.
2. Make the displayed participant information/consent text match the approved materials.
3. Set these Streamlit secrets:

```toml
RESEARCH_MODE = "true"
RESEARCH_CONSENT_VERSION = "APPROVED_VERSION_OR_DATE"
RESEARCH_APPROVAL_REFERENCE = "APPROVAL_OR_PROTOCOL_REFERENCE"
RESEARCH_ADMIN_EMAILS = "founder@intonasphereai.org"
RESEARCH_CONSENT_TEXT = """PASTE THE APPROVED PARTICIPANT INFORMATION / CONSENT TEXT HERE"""
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SERVICE_ROLE_KEY"
```

4. Reboot/redeploy the Streamlit app after changing secrets.
5. Test research enrollment with a non-production test session before broadly advertising participation.

## C. Research v1.0 data fields

### `research_participants`
Anonymous participant ID/code, consent version, age-18+ confirmation, optional French proficiency, optional broad French-language background, enrollment time.

### `research_sessions`
Anonymous participant/session IDs, consent version, app version, session start time.

### `research_events`
Anonymous participant/session IDs, event type, activity type, timestamp, and aggregate JSON metrics.

Current instrumented events:
- `pronunciation_analysis`
- `grammar_answer_checked`
- `guided_section_submitted`
- `research_enrollment`
- `research_session_left`

### `beta_feedback`
1–5 rating, feedback category, message, timestamp, and anonymous research code only if the person is already participating in research.

## D. Important security rule

Never commit `.streamlit/secrets.toml`, SMTP passwords, or the Supabase service-role key to GitHub. The service-role key must exist only in the server-side deployment secrets.
