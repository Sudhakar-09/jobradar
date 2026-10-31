"""Normalizer domain: ingest, dedupe and (from Phase 3) normalization of the shared job corpus."""

from jobradar.normalizer.rules import normalize_company
from jobradar.normalizer.service import IngestResult, ingest, job_country

__all__ = ["IngestResult", "ingest", "job_country", "normalize_company"]
