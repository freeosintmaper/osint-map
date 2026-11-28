# Security Policy

## Supported version

Security fixes are made against the latest code on the default branch (`main`).

## Reporting a vulnerability

Please do not publish exploitable details, credentials, tokens, or proof-of-concept payloads in a public issue.

When private vulnerability reporting is available for this repository, use **Security → Advisories → Report a vulnerability** on GitHub. If that option is unavailable, contact the repository owner privately through the contact options on the owner's GitHub profile. Include the affected component, impact, and a minimal reproduction; do not include real user data or secrets.

## Security boundaries

- The map frontend is public. Any value shipped to the browser must be treated as public; secrets and privileged credentials belong only in server-side configuration.
- Browser-side login state, hidden controls, and CORS are not authorization boundaries. Database access must remain protected by Supabase grants and Row Level Security.
- The zone AI function must authenticate requests and authorize the administrator before calling paid external AI services. Rate limiting and spending controls are separate protections and must be enforced at the service boundary.
- Backups are not considered a recovery guarantee until a restore has been tested.
- Changes to map data, zone geometry, event coordinates, and source datasets must not be mixed into security-only changes unless they are explicitly required and reviewed.

## Security checks

The repository runs CodeQL analysis for JavaScript and Python on changes to `main`, pull requests, and a weekly schedule. Findings should be reviewed and fixed according to their severity and reachability.


## Production configuration

- Keep Supabase self-service sign-ups and anonymous sign-ins disabled. The browser login form is not a substitute for disabling sign-ups in Supabase Auth.
- Keep the access-token JWT expiry at the Supabase default of 3,600 seconds unless the application has a tested reason to change it. Time-boxed and inactivity session limits are plan-dependent.
- Enable leaked-password protection when the Supabase plan supports it.
- Keep GitHub two-factor authentication, Secret Scanning, Push Protection, Dependabot alerts, and GitHub Pages HTTPS enforcement enabled for the repository and owner account.
- The Supabase publishable/anon key in the static frontend is public by design. It must never be treated as a secret; RLS and database grants are the authorization boundary. Never place a service-role key or AI provider key in frontend files.
- The map UI calls `public.is_osint_map_admin()` before showing administrator controls. Database RLS independently checks the server-side administrator allow-list and the active Auth session.
- The zone AI Edge Function allows the production GitHub Pages origin by default. Exact additional development origins may be added to the server-side `ZONE_AI_ALLOWED_ORIGINS` setting; do not use wildcards or place this setting in frontend code.
- The Content Security Policy blocks inline scripts and restricts script loading to same-origin files. Inline styles remain allowed for the current map UI; this is a compatibility concession, not permission to place inline JavaScript in HTML.

### Initial administrator bootstrap

The administrator allow-list is intentionally not populated by automatically promoting the first account. After creating the trusted owner account in Supabase Auth, run this once in the Supabase SQL Editor, replacing the placeholder with that account's email:

```sql
insert into private.osint_map_admins (user_id)
select id
from auth.users
where lower(email) = lower('OWNER_EMAIL')
on conflict (user_id) do nothing;
```

Do not use this query to add ordinary users. The production project already has its administrator entry; do not run this bootstrap again unless rebuilding a separate project.
