"""Normalizer domain: ingest, dedupe and (from Phase 3) normalization of the shared job corpus."""

from jobradar.normalizer.rules import LanguageSignals, normalize_company
from jobradar.normalizer.service import (
    IngestResult,
    ingest,
    job_country,
    job_language_signals,
)

__all__ = [
    "IngestResult",
    "LanguageSignals",
    "ingest",
    "job_country",
    "job_language_signals",
    "normalize_company",
]
