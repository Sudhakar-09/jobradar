"""Celery entry point for workers and beat (`celery -A jobradar.tasks.celery_app`).

The application itself is infrastructure and lives in `jobradar.core.queue`, so that `core`
(for example the readiness check) never imports from an entry-point package.
"""

from jobradar.core.queue import celery_app

__all__ = ["celery_app"]
