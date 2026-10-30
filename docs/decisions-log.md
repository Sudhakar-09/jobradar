# Decisions log

## 2026-10-30

Initial record of decisions previously agreed in chat. Their original decision dates are not
available in the repository.

- **Project name:** JobRadar (`jobradar`).
- **Architecture:** modular monolith, organized around the product domains and responsibilities
  defined in `CLAUDE.md`.
- **Logged-in portal execution:** use a home runner on the user's machine; portal logins and browser
  credentials remain local and cookies are never uploaded.
- **LinkedIn and Indeed applications:** LinkedIn Easy Apply and Indeed Apply are one-tap lanes only.
  The system prepares materials and links for the user; it does not automate submission.
- **Repository visibility:** the GitHub repository is intended to be private.
- **Project location:** project lives at `C:\dev\jobradar`, never in OneDrive. The OneDrive copy
  remains only as a retained backup and must not be used for ongoing work.
- **Phase 1 market and role packs:** use United States as the additional market and Software
  Engineer as the initial role pack; India remains the base market. These starter packs do not
  assert that they are the user's complete job-search preferences.
- **Profile parsing:** declare PyYAML directly for YAML loading. The initial resume parser supports
  UTF-8 plain text only and extracts explicit labels rather than inferring profile facts.
