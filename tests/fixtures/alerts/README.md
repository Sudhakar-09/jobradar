# Job-alert email fixtures

Synthetic `.eml` files, one per parser, written in the typical structure of each board's alert
emails (job cards with a linked title followed by company and location lines, tracking
parameters, redirect wrappers, image links duplicating a job, footer links). Companies, job IDs,
recipients and addresses are fictional.

They are **not** copies of real emails. After the owner connects Gmail (Phase 2f), real alerts
are checked against these parsers; any format difference is fixed in `config/alert_senders.yaml`
and recorded with a new anonymized fixture here (real company/title text replaced, IDs changed,
tracking tokens removed).
