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
