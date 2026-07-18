from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Callable
from datetime import date

from core.models import Plan
from fastapi import FastAPI
from simulation.result import SimulationResult

CACHE_MAX_SIZE = 8
_STATE_ATTR = "simulation_cache"

CacheKey = tuple[int, str, str | None, str | None, str]
RunSimulation = Callable[..., SimulationResult]


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
    fred_api_key: str | None,
    eod_api_key: str | None,
    run: RunSimulation,
    today: date | None = None,
) -> SimulationResult:
    resolved_today = today or date.today()
    key: CacheKey = (
        plan_id,
        fingerprint_plan(plan),
        fred_api_key,
        eod_api_key,
        resolved_today.isoformat(),
    )
    cache = _cache_for(app)
    cached = cache.get(key)
    if cached is not None:
        cache.move_to_end(key)
        return cached

    result = run(
        plan,
        allow_refresh=True,
        fred_api_key=fred_api_key,
        eod_api_key=eod_api_key,
        today=resolved_today,
    )
    cache[key] = result
    cache.move_to_end(key)
    while len(cache) > CACHE_MAX_SIZE:
        cache.popitem(last=False)
    return result
