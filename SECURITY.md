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
