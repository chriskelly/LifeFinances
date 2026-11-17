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
_KEYS_ATTR = "simulation_keys"

CacheKey = tuple[int, str, str | None, str | None, str]
# One entry per plan: (previous key, current key). The summary shows one step
# back, so a history list would be unused state.
KeysEntry = tuple[CacheKey | None, CacheKey | None]
RunSimulation = Callable[..., SimulationResult]

logger = logging.getLogger(__name__)


def fingerprint_plan(plan: Plan) -> str:
    # Name and the reporting threshold are display-only; neither busts the cache.
    payload = plan.model_dump_json(exclude={"name", "summary_spending_threshold"})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_for(app: FastAPI) -> OrderedDict[CacheKey, SimulationResult]:
    cache = getattr(app.state, _STATE_ATTR, None)
    if cache is None:
        cache = OrderedDict()
        setattr(app.state, _STATE_ATTR, cache)
    return cache


def _keys_for(app: FastAPI) -> dict[int, KeysEntry]:
    keys = getattr(app.state, _KEYS_ATTR, None)
    if keys is None:
        keys = {}
        setattr(app.state, _KEYS_ATTR, keys)
    return keys


def previous_result(app: FastAPI, *, plan_id: int) -> SimulationResult | None:
    """The result rendered before the current one, if it is still cached."""
    keys = getattr(app.state, _KEYS_ATTR, None)
    if keys is None:
        return None
    previous_key, _current_key = keys.get(plan_id, (None, None))
    if previous_key is None:
        return None
    return _cache_for(app).get(previous_key)


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
        keys = _keys_for(app)
        _previous_key, current_key = keys.get(plan_id, (None, None))
        if key != current_key:
            # Revisiting an earlier plan is a cache hit, but it is still the
            # newest result the panel shows, so the next change must compare
            # against it. Repeated renders of the same key leave the pair alone.
            keys[plan_id] = (current_key, key)
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
    keys = _keys_for(app)
    _previous_key, current_key = keys.get(plan_id, (None, None))
    keys[plan_id] = (current_key, key)
    cache[key] = result
    cache.move_to_end(key)
    while len(cache) > CACHE_MAX_SIZE:
        cache.popitem(last=False)
    return result
