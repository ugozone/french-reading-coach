# Teacher Access Protocol

Student use remains open: students can use the learning tools in guest mode without creating an account.

## Teacher workflow

1. A prospective teacher opens **Request Teacher Access** in the sidebar.
2. The teacher submits name, email, institution (optional), and a short message (optional).
3. The request is stored in `teacher_access_requests` with `status = pending`. It does **not** grant access.
4. The administrator reviews the request in the Supabase dashboard.
5. If approved, the administrator:
   - creates or invites that email in **Supabase Authentication → Users**;
   - verifies/ensures the email is confirmed according to the project's Auth settings;
   - adds or updates the same email in `teacher_access`;
   - sets the teacher's real `full_name` / `teacher_name`;
   - sets `role = teacher` (or `admin` when appropriate);
   - sets `is_active = true`;
   - sets `invite_status = accepted`.
6. The teacher uses **Teacher sign in** with that exact approved email and password.
7. The app matches the signed-in email to the active `teacher_access` record and loads that teacher's real name into the dashboard.
8. A signed-in but inactive/unapproved email cannot open the Teacher Dashboard.

## One-time database setup

Run `TEACHER_ACCESS_SETUP.sql` in the Supabase SQL Editor before using the public request form.

## Recommended approval example

```sql
insert into public.teacher_access
    (teacher_name, full_name, email, role, is_active, invite_status, invited_by)
values
    ('Marie', 'Marie Dupont', 'marie@example.com', 'teacher', true, 'accepted', 'Jamike')
on conflict (email) do update set
    teacher_name = excluded.teacher_name,
    full_name = excluded.full_name,
    role = excluded.role,
    is_active = excluded.is_active,
    invite_status = excluded.invite_status,
    invited_by = excluded.invited_by,
    updated_at = now();
```

Do not create a public "Teacher Sign Up" path that can set `is_active = true`.


## Administrator email notification

Every new teacher-access request is emailed automatically to **founder@intonasphereai.org** after it is stored in Supabase. Configure the secure SMTP secrets described in `EMAIL_NOTIFICATION_SETUP.md`. The recipient address is fixed in the application; SMTP credentials are never stored in source code.
