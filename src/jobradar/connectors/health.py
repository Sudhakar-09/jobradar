"""Connector health rules (US-2.6): pure functions, no I/O."""

from typing import Final, Literal

RunStatus = Literal["ok", "partial", "degraded"]

INVALID_RATIO_DEGRADED: Final = 0.2  # ≥ 20 % of items failing validation = schema drift
MIN_AVERAGE_FOR_ALERTS: Final = 5.0  # drop/zero rules apply to sources averaging ≥ 5 jobs
DROP_RATIO_DEGRADED: Final = 0.3  # fewer than 30 % of the 7-day average = > 70 % drop


def evaluate_health(found: int, invalid: int, average_found: float | None) -> RunStatus:
    """Classify a finished run.

    Args:
        found: Jobs parsed successfully in this run.
        invalid: Items that failed validation.
        average_found: Average ``found`` over the previous 7 days, or None without history.

    Returns:
        ``degraded`` for likely schema drift, or an empty or sharply dropped (> 70 %) source that
        usually has at least 5 jobs; ``partial`` when some items were invalid; otherwise ``ok``.
    """
    total = found + invalid
    if total and invalid / total >= INVALID_RATIO_DEGRADED:
        return "degraded"
    # Quiet sources (average below the threshold) swing too much for drop alerts.
    if (
        average_found is not None
        and average_found >= MIN_AVERAGE_FOR_ALERTS
        and found < DROP_RATIO_DEGRADED * average_found  # includes found == 0
    ):
        return "degraded"
    return "partial" if invalid else "ok"
