from __future__ import annotations

from decimal import Decimal

from core.job import Job
from core.streams import TimedStream
from core.timeline import Timeline, project_stream

_MONTHS_PER_YEAR = Decimal(12)


def _segments(
    job: Job, timeline: Timeline, job_start: int, job_end: int
) -> list[tuple[int, int, Decimal]]:
    """(start_index, end_index, remaining_fraction) segments covering the job."""
    segments: list[tuple[int, int, Decimal]] = []
    cursor = job_start
    for window in job.sabbaticals:
        window_start = timeline.index_of(window.start)
        window_end = timeline.index_of(window.end)
        if window_start > cursor:
            segments.append((cursor, window_start - 1, Decimal(1)))
        segments.append((window_start, window_end, window.remaining_fraction))
        cursor = window_end + 1
    if cursor <= job_end:
        segments.append((cursor, job_end, Decimal(1)))
    return segments


def _segment_stream(
    base_monthly: Decimal,
    remaining: Decimal,
    segment_start: int,
    job_start: int,
    growth: Decimal,
    timeline: Timeline,
    segment_end: int,
) -> TimedStream:
    anchor_exponent = Decimal(segment_start - job_start) / _MONTHS_PER_YEAR
    segment_base = base_monthly * remaining * (Decimal(1) + growth) ** anchor_exponent
    return TimedStream(
        monthly_amount=segment_base,
        start=timeline.month_boundary(segment_start),
        end=timeline.month_boundary(segment_end),
        annual_growth_rate=growth,
        is_nominal=False,
    )


def project_job_gross(job: Job, timeline: Timeline) -> list[Decimal]:
    """Project one job to a horizon-length monthly gross series (sabbaticals applied)."""
    horizon = timeline.horizon_months
    series = [Decimal("0.00")] * horizon
    if horizon <= 0:
        return series

    base_monthly = job.annual_income / _MONTHS_PER_YEAR
    growth = job.annual_raise
    job_start = 0 if job.start is None else timeline.index_of(job.start)
    job_end = horizon - 1 if job.end is None else timeline.index_of(job.end)

    for segment_start, segment_end, remaining in _segments(
        job, timeline, job_start, job_end
    ):
        if segment_start > segment_end:
            continue
        stream = _segment_stream(
            base_monthly,
            remaining,
            segment_start,
            job_start,
            growth,
            timeline,
            segment_end,
        )
        segment_series = project_stream(stream, timeline)
        for i in range(horizon):
            series[i] += segment_series[i]
    return series
