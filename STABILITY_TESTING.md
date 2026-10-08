# French Reading Coach — Stability Fix (test branch)

This branch is deliberately separate from `main`. Do **not** change the live Community Cloud application's branch before verifying a test deployment.

## Changes made

- `speech.py`: defer the Whisper import and tiny-model download until a recording is analyzed; share the cached model; serialize CPU-heavy inference to avoid multiple simultaneous Whisper runs; clean up transient DOCX/audio files.
- `app.py`: cache seed-data initialization for 1 hour instead of issuing Supabase upserts after every Streamlit widget interaction; remove temporary WAV files after transcription or acoustic extraction, without removing audio before the acoustic analysis.
- `auth.py`: create a separate Supabase **Auth** client in `st.session_state` for each teacher session. The existing anonymous table client and server-only Supabase database logic remain in place.
- `requirements.txt`: use a pinned dependency stack, with CPU-only PyTorch on Linux to avoid NVIDIA/CUDA installation. The branch's test target is **Python 3.12**.
- `tests/test_stability.py`: ensure transcription output remains correct, temporary recordings are cleaned on success/failure, and teacher Auth clients are not shared between sessions.
- `.github/workflows/stability-smoke.yml`: run dependency installation, byte-compilation, CPU-only verification and regression tests on pushes to this branch and on pull requests.

## Test deployment — do not modify production

1. Leave the existing `main`-based Streamlit app at its original URL.
2. In Streamlit Community Cloud, create a **new app** from repository `ugozone/french-reading-coach`, branch `stability-fix`, entrypoint `app.py`. Pick a **different** subdomain.
3. In **Advanced settings**, explicitly choose **Python 3.12**. Existing Community Cloud apps cannot be upgraded to a different Python major/minor version in-place; create this new test deployment instead.
4. Configure the test app's secrets securely in Community Cloud settings. Do not commit keys or passwords to GitHub. Prefer a dedicated Supabase test project to avoid test activity entering production student data.
5. Wait for installation and first launch. Check logs for successful startup, without CUDA package downloads or `Killed` / OOM / traceback messages.
6. Test at least two browsers simultaneously: teacher login, sign-out, reading lessons, IPA, text/PDF/DOCX upload, grammar game, student progress, recording/transcription, F0/formant calculations, guided tasks, and teacher dashboards. Confirm account isolation across browser sessions.
7. Repeat with multiple simultaneous student recordings. Check log and resource use; a single Streamlit instance queues Whisper transcriptions in this branch.
8. Run long enough to confirm the crash during active usage is resolved. Then review the pull request, and merge only after successful acceptance testing.

## Important limitations

- This branch **does not** disable Streamlit Community Cloud's inactivity hibernation. An always-on hosting service is needed for continuous availability.
- Local Whisper still consumes significant memory when students analyze speech. Loading it lazily and serializing calls reduces peak load but cannot guarantee zero out-of-memory crashes.
- Teacher sign-in in `st.session_state` is scoped to a connected browser session; a Streamlit restart or dropped session may require signing in again.
- This branch does not alter Supabase tables, student account contents, access approvals or lesson/question definitions.
- Database seeding still occurs periodically (at most once per running process/hour), for compatibility. Moving it to a one-time migration is recommended for the next deployment iteration.
- Before storing student audio persistently, review consent, retention and access-control requirements.

## Rollback

- **Before merging:** simply stop the separate test deployment. The original production `main` branch is unchanged.
- **After merging:** revert the merge commit using GitHub's revert process, then review deployment logs. Do not delete or recreate the Supabase database.

## Diagnostic evidence needed if problems remain

Capture the final **100–200 log lines at the instant a student receives the 'Contact the app builder' screen**, plus the action they performed (e.g. uploading audio, recording, signing in, or opening a dashboard), the time and the number of concurrent students. General package installation logs alone cannot prove why a runtime process stopped.
