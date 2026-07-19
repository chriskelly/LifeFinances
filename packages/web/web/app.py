from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from core.models import AppSettings, Plan
from core.paths import default_db_path
from core.plan_names import untitled_plan_name
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from simulation.result import SimulationResult
from simulation.stub import run_simulation

from web import charts, forms, routes, sections
from web.dependencies import get_repository, require_plan, resolve_default_plan_id
from web.forms import AppSettingsForm, HouseholdForm, PortfolioForm
from web.routes import (
    EDITOR_HOUSEHOLD,
    EDITOR_PORTFOLIO,
    EDITOR_SETTINGS,
    HOME,
    PLAN_CREATE,
    PLAN_DELETE,
    PLAN_DUPLICATE,
    PLAN_HOUSEHOLD,
    PLAN_PORTFOLIO,
    PLAN_RENAME,
    PLAN_SET_DEFAULT,
    PLAN_SETTINGS,
    RESULTS,
)
from web.simulation_cache import get_or_run_simulation

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_PACKAGE_DIR / "templates"))
templates.env.globals["routes"] = routes
templates.env.globals["sections"] = sections
templates.env.globals["forms"] = forms

_INIT_DB_MESSAGE = "No database found. Run: uv run python scripts/init_db.py"
_SIMULATION_FAILURE_MESSAGE = "Simulation failed. Check plan inputs and try again."

_FIELD_LABELS = {
    "birth_month": "Birth month",
    "birth_year": "Birth year",
    "max_age_years": "Max age",
    "current_savings_balance": "Total savings balance",
}


def _validation_message(exc: ValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        field = str(err["loc"][-1]) if err["loc"] else ""
        label = _FIELD_LABELS.get(field, field or "Value")
        parts.append(f"{label}: {err['msg']}")
    return "; ".join(parts)


def _figure_json(figure: dict) -> str:
    # Escape "<" so user-influenced labels cannot break out of </script>.
    return json.dumps(figure).replace("<", "\\u003c")


def _load_simulation(
    request: Request,
    *,
    plan_id: int,
    plan_model: Plan,
    settings: AppSettings,
) -> tuple[SimulationResult | None, str | None]:
    try:
        return (
            get_or_run_simulation(
                request.app,
                plan_id=plan_id,
                plan=plan_model,
                fred_api_key=settings.fred_api_key,
                eod_api_key=settings.eod_api_key,
                run=run_simulation,
            ),
            None,
        )
    except Exception:
        logger.exception("Simulation failed for plan_id=%s", plan_id)
        return None, _SIMULATION_FAILURE_MESSAGE


def _resolve_db_path(app: FastAPI) -> Path:
    db_path = app.state.db_path
    if db_path is None:
        return default_db_path()
    return db_path


def get_repo(request: Request) -> PlanRepository:
    return get_repository(_resolve_db_path(request.app))


def get_settings_repo(request: Request) -> SettingsRepository:
    return SettingsRepository(db_path=_resolve_db_path(request.app))


RepoDep = Annotated[PlanRepository, Depends(get_repo)]
SettingsRepoDep = Annotated[SettingsRepository, Depends(get_settings_repo)]


def _redirect_to_plan(plan_id: int) -> RedirectResponse:
    return RedirectResponse(url=f"{HOME}?plan={plan_id}", status_code=302)


def _redirect_after_plan_delete(
    *,
    repo: PlanRepository,
    settings_repo: SettingsRepository,
    deleted_id: int,
    return_plan: int | None,
) -> RedirectResponse:
    if (
        return_plan is not None
        and return_plan != deleted_id
        and return_plan in repo.loadable_ids()
    ):
        return _redirect_to_plan(return_plan)
    new_default_id, _ = repo.ensure_bootstrap(settings_repo=settings_repo)
    return _redirect_to_plan(new_default_id)


def _mount_static(web_app: FastAPI) -> None:
    web_app.mount(
        routes.STATIC,
        StaticFiles(directory=_PACKAGE_DIR / "static"),
        name="static",
    )


def _register_home_route(web_app: FastAPI) -> None:
    @web_app.get(HOME, response_class=HTMLResponse)
    def home(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> Response:
        resolved_db_path = _resolve_db_path(request.app)
        if not resolved_db_path.exists():
            return templates.TemplateResponse(
                request,
                "error.html",
                {"message": _INIT_DB_MESSAGE},
            )

        settings_repo = get_settings_repo(request)
        if plan is None:
            default_plan_id = resolve_default_plan_id(
                plan_repo=repo, settings_repo=settings_repo
            )
            return _redirect_to_plan(default_plan_id)

        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        settings = settings_repo.get()
        result, simulation_error = _load_simulation(
            request,
            plan_id=plan_id,
            plan_model=plan_model,
            settings=settings,
        )
        summaries = repo.list()
        loadable_ids = repo.loadable_ids()
        chart_type = charts.DEFAULT_CHART
        context = {
            "plan_id": plan_id,
            "plan": plan_model,
            "result": result,
            "settings": settings,
            "summaries": summaries,
            "loadable_ids": loadable_ids,
            "loadable_count": len(loadable_ids),
            "chart_type": chart_type,
            "simulation_error": simulation_error,
            "chart_options": charts.chart_options(result) if result is not None else [],
            "chart_figure_json": (
                _figure_json(charts.build_figure(result, chart_type))
                if result is not None
                else None
            ),
        }
        return templates.TemplateResponse(
            request,
            "index.html",
            context,
        )


def _register_editor_routes(web_app: FastAPI) -> None:
    @web_app.get(EDITOR_HOUSEHOLD, response_class=HTMLResponse)
    def editor_household(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return templates.TemplateResponse(
            request,
            "editor_household.html",
            {"plan_id": plan_id, "plan": plan_model},
        )

    @web_app.get(EDITOR_PORTFOLIO, response_class=HTMLResponse)
    def editor_portfolio(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return templates.TemplateResponse(
            request,
            "editor_portfolio.html",
            {"plan_id": plan_id, "plan": plan_model},
        )

    @web_app.get(EDITOR_SETTINGS, response_class=HTMLResponse)
    def editor_settings(
        request: Request,
        repo: RepoDep,
        settings_repo: SettingsRepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, _ = require_plan(plan, plan_repo=repo)
        settings = settings_repo.get()
        return templates.TemplateResponse(
            request,
            "editor_settings.html",
            {"plan_id": plan_id, "settings": settings},
        )


def _register_patch_routes(web_app: FastAPI) -> None:
    @web_app.patch(PLAN_HOUSEHOLD)
    def patch_household(
        person1_birth_month: Annotated[int, Form()],
        person1_birth_year: Annotated[int, Form()],
        person1_max_age_years: Annotated[int, Form()],
        filing_status: Annotated[str, Form()],
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
        residence_state: Annotated[str | None, Form()] = None,
        ss_pension_taxable_fraction: Annotated[Decimal, Form()] = Decimal("0.80"),
        social_security_trust_factor: Annotated[Decimal, Form()] = Decimal(1),
        has_partner: Annotated[bool, Form()] = False,
        person2_birth_month: Annotated[int | None, Form()] = None,
        person2_birth_year: Annotated[int | None, Form()] = None,
        person2_max_age_years: Annotated[int | None, Form()] = None,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        try:
            updated = HouseholdForm(
                person1_birth_month=person1_birth_month,
                person1_birth_year=person1_birth_year,
                person1_max_age_years=person1_max_age_years,
                filing_status=filing_status,  # type: ignore[arg-type]
                residence_state=residence_state,
                ss_pension_taxable_fraction=ss_pension_taxable_fraction,
                social_security_trust_factor=social_security_trust_factor,
                has_partner=has_partner,
                person2_birth_month=person2_birth_month,
                person2_birth_year=person2_birth_year,
                person2_max_age_years=person2_max_age_years,
            ).apply_to(plan_model)
        except ValidationError as exc:
            return HTMLResponse(_validation_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)

    @web_app.patch(PLAN_PORTFOLIO)
    def patch_portfolio(
        current_savings_balance: Annotated[Decimal, Form()],
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        try:
            updated = PortfolioForm(
                current_savings_balance=current_savings_balance,
            ).apply_to(plan_model)
        except ValidationError as exc:
            return HTMLResponse(_validation_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)

    @web_app.patch(PLAN_SETTINGS)
    def patch_settings(
        repo: RepoDep,
        settings_repo: SettingsRepoDep,
        plan: Annotated[int | None, Query()] = None,
        fred_api_key: Annotated[str | None, Form()] = None,
        clear_fred_api_key: Annotated[bool, Form()] = False,
        eod_api_key: Annotated[str | None, Form()] = None,
        clear_eod_api_key: Annotated[bool, Form()] = False,
    ) -> Response:
        require_plan(plan, plan_repo=repo)
        current = settings_repo.get()
        updated = AppSettingsForm(
            fred_api_key=fred_api_key,
            clear_fred_api_key=clear_fred_api_key,
            eod_api_key=eod_api_key,
            clear_eod_api_key=clear_eod_api_key,
        ).apply_to(current)
        settings_repo.save(updated)
        return Response(status_code=200)


def _register_plan_management_routes(web_app: FastAPI) -> None:
    @web_app.post(PLAN_CREATE)
    def create_plan(repo: RepoDep, settings_repo: SettingsRepoDep) -> Response:
        name = untitled_plan_name(existing=[s.name for s in repo.list()])
        new_id, _ = repo.create(name=name)
        settings = settings_repo.get()
        if settings.default_plan_id is None:
            settings_repo.save(settings.model_copy(update={"default_plan_id": new_id}))
        return _redirect_to_plan(new_id)

    @web_app.post(PLAN_DUPLICATE)
    def duplicate_plan(repo: RepoDep, plan_id: int) -> Response:
        require_plan(plan_id, plan_repo=repo)
        new_id, _ = repo.duplicate(plan_id)
        return _redirect_to_plan(new_id)

    @web_app.post(PLAN_RENAME)
    def rename_plan(
        repo: RepoDep,
        plan_id: int,
        name: Annotated[str, Form()],
    ) -> Response:
        require_plan(plan_id, plan_repo=repo)
        try:
            repo.rename(plan_id, name=name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _redirect_to_plan(plan_id)

    @web_app.post(PLAN_SET_DEFAULT)
    def set_default_plan(
        repo: RepoDep, settings_repo: SettingsRepoDep, plan_id: int
    ) -> Response:
        require_plan(plan_id, plan_repo=repo)
        settings = settings_repo.get()
        settings_repo.save(settings.model_copy(update={"default_plan_id": plan_id}))
        return _redirect_to_plan(plan_id)

    @web_app.post(PLAN_DELETE)
    def delete_plan(
        repo: RepoDep,
        settings_repo: SettingsRepoDep,
        plan_id: int,
        return_plan: Annotated[int | None, Form()] = None,
    ) -> Response:
        if not repo.exists(plan_id):
            raise HTTPException(status_code=404, detail="Plan not found")
        try:
            repo.delete(plan_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return _redirect_after_plan_delete(
            repo=repo,
            settings_repo=settings_repo,
            deleted_id=plan_id,
            return_plan=return_plan,
        )


def _register_results_route(web_app: FastAPI) -> None:
    @web_app.get(RESULTS, response_class=HTMLResponse)
    def results(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
        chart: Annotated[str | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        settings = get_settings_repo(request).get()
        result, simulation_error = _load_simulation(
            request,
            plan_id=plan_id,
            plan_model=plan_model,
            settings=settings,
        )
        chart_type = charts.resolve_chart_type(chart)
        if result is None:
            return templates.TemplateResponse(
                request,
                "results.html",
                {
                    "plan_id": plan_id,
                    "result": None,
                    "chart_type": chart_type,
                    "chart_options": [],
                    "chart_figure_json": None,
                    "simulation_error": simulation_error or _SIMULATION_FAILURE_MESSAGE,
                },
            )
        figure = charts.build_figure(result, chart_type)
        return templates.TemplateResponse(
            request,
            "results.html",
            {
                "plan_id": plan_id,
                "result": result,
                "chart_type": chart_type,
                "chart_options": charts.chart_options(result),
                "chart_figure_json": _figure_json(figure),
                "simulation_error": None,
            },
        )


def create_app(*, db_path: Path | None = None) -> FastAPI:
    web_app = FastAPI()
    web_app.state.db_path = db_path

    _mount_static(web_app)
    _register_home_route(web_app)
    _register_editor_routes(web_app)
    _register_patch_routes(web_app)
    _register_plan_management_routes(web_app)
    _register_results_route(web_app)

    return web_app


app = create_app()
