"""SQLAlchemy models. Importing this package registers every table on ``Base.metadata``."""

from jobradar.models.accounts import User
from jobradar.models.connectors import (
    AlertInbox,
    AlertMessage,
    Company,
    CompanySuggestion,
    SourceRun,
)
from jobradar.models.core import AuditLog, DeadLetter, SettingsFlag
from jobradar.models.jobs import Job, JobSource
from jobradar.models.privacy import Consent

__all__ = [
    "AlertInbox",
    "AlertMessage",
    "AuditLog",
    "Company",
    "CompanySuggestion",
    "Consent",
    "DeadLetter",
    "Job",
    "JobSource",
    "SettingsFlag",
    "SourceRun",
    "User",
]
