from __future__ import annotations

from collections.abc import Iterable


def choose_daily_bar_cohort_key(
    cohort_counts: Iterable[tuple[str | None, str | None, int]],
) -> tuple[str, str] | None:
    normalized = [
        (provider or "", adjustment or "", int(row_count))
        for provider, adjustment, row_count in cohort_counts
        if row_count > 0
    ]
    if not normalized:
        return None

    provider, adjustment, _ = sorted(
        normalized,
        key=lambda item: (-item[2], item[0], item[1]),
    )[0]
    return provider, adjustment
