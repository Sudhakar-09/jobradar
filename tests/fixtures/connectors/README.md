# Connector fixtures

Synthetic responses in the exact JSON shape of each public ATS API (shapes checked against the
live APIs on 2026-10-30; no real postings are stored). Companies, jobs and URLs are fictional.
Each file contains at least one deliberately invalid item to exercise schema-drift counting.
Workable's posting fields follow its documented widget format (the probed account had no open
jobs); `jobradar companies verify` re-checks the live shape in Phase 2g.
