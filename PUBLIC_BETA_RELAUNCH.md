# French Reading Coach — Public Research Beta v1.0

## Public launch mode
Students can use Pronunciation, Grammar, and Guided Reading immediately as guests. A student profile remains optional and is only for saved progress, assignments, and teacher tracking.

The public banner identifies the app as a free beta. No payment or student sign-up is required.

## Research mode is OFF by default
The app ships with `RESEARCH_MODE = "false"`. In this state:

- the learning app remains fully usable;
- no research participant is enrolled;
- no research session/event is written;
- the Research Beta tab explains that research collection is not active.

Do not change this setting to `true` until the applicable institutional review/authorization is in place and the displayed consent language matches the approved protocol.

## Before enabling research
1. In Supabase, open **SQL Editor**.
2. Run `PUBLIC_RESEARCH_BETA_SETUP.sql` once. You can do this before research activation so the separate beta-feedback form works during the free usability pilot.
3. In Streamlit secrets, configure `SUPABASE_SERVICE_ROLE_KEY` for researcher/admin export. Never commit this key to GitHub.
4. Update the consent/information text in `app.py` to match the approved study materials exactly.
5. Set `RESEARCH_CONSENT_VERSION` to the approved consent version/date.
6. Only then set `RESEARCH_MODE = "true"`.

## Data minimization in v1.0
Research enrollment is 18+ only for this pilot build and stores:

- anonymous participant code;
- consent version and consent timestamp;
- self-reported French level (optional);
- broad language background (optional);
- activity/session IDs and aggregate performance measures.

The research event logger is deliberately designed not to receive names, email addresses, raw audio, pasted free text, or speech transcripts.

## Research events currently instrumented
When research mode is enabled and a participant voluntarily enrolls, the app can store aggregate measures from:

- pronunciation analysis: score, word counts, input mode, and feedback-item count;
- grammar: lesson/question IDs, level, correctness, and XP;
- guided reading: task/section IDs, pronunciation score, comprehension correctness, and vocabulary correctness.

## Beta feedback
The Research Beta tab also contains a simple feedback form. Feedback is kept in `beta_feedback`, separate from the research dataset. Do not treat operational feedback as research data unless your approved protocol/consent permits that use.

## Admin export
A signed-in user whose email is listed in `RESEARCH_ADMIN_EMAILS` can access the Research Admin section inside the Teacher Dashboard. Admin export requires `SUPABASE_SERVICE_ROLE_KEY` in Streamlit secrets.

The default research admin email is:

`founder@intonasphereai.org`

## Suggested public deployment
1. Push this project to a private or public GitHub repository (without secrets).
2. Deploy `app.py` on Streamlit Community Cloud.
3. Add Supabase, SMTP, and research settings through Streamlit **Secrets**.
4. Test guest learning in an incognito browser before sharing the public URL.
