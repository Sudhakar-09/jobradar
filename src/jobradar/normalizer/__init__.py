"""Normalizer domain: ingest, dedupe and (from Phase 3) normalization of the shared job corpus."""

from jobradar.normalizer.service import IngestResult, ingest

__all__ = ["IngestResult", "ingest"]
