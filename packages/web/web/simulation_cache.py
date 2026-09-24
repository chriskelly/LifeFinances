from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from collections.abc import Callable
from datetime import date

from core.models import AppSettings, Plan
from fastapi import FastAPI
from simulation.result import SimulationResult
from simulation.stub import run_simulation

CACHE_MAX_SIZE = 8
_STATE_ATTR = "simulation_cache"

CacheKey = tuple[int, str, str | None, str | None, str]
RunSimulation = Callable[..., SimulationResult]

logger = logging.getLogger(__name__)


def fingerprint_plan(plan: Plan) -> str:
    # Name is display-only; renaming must not bust the sim cache.
    payload = plan.model_dump_json(exclude={"name"})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_for(app: FastAPI) -> OrderedDict[CacheKey, SimulationResult]:
    cache = getattr(app.state, _STATE_ATTR, None)
    if cache is None:
        cache = OrderedDict()
        setattr(app.state, _STATE_ATTR, cache)
    return cache


def get_or_run_simulation(
    app: FastAPI,
    *,
    plan_id: int,
    plan: Plan,
    settings: AppSettings,
    run: RunSimulation | None = None,
    today: date | None = None,
) -> SimulationResult:
    resolved_run = run_simulation if run is None else run
    resolved_today = today or date.today()
    key: CacheKey = (
        plan_id,
        fingerprint_plan(plan),
        settings.fred_api_key,
        settings.eod_api_key,
        resolved_today.isoformat(),
    )
    cache = _cache_for(app)
    cached = cache.get(key)
    if cached is not None:
        cache.move_to_end(key)
        return cached

    try:
        result = resolved_run(
            plan,
            allow_refresh=True,
            fred_api_key=settings.fred_api_key,
            eod_api_key=settings.eod_api_key,
            today=resolved_today,
        )
    except Exception:
        logger.exception("Simulation failed for plan_id=%s", plan_id)
        raise
    cache[key] = result
    cache.move_to_end(key)
    while len(cache) > CACHE_MAX_SIZE:
        cache.popitem(last=False)
    return result
