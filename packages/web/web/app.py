from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from core.models import AppSettings, Household, Plan
from core.paths import default_db_path
from core.plan_names import untitled_plan_name
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from domain.social_security.earnings import parse_social_security_statement_xml
from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from simulation.result import SimulationResult
from simulation.stub import run_simulation

from web import (
    boundaries,
    charts,
    currency,
    forms,
    percent,
    routes,
    sections,
    spending_summary,
)
from web.dependencies import get_repository, require_plan, resolve_default_plan_id
from web.forms import (
    AppSettingsForm,
    HouseholdForm,
    JobsForm,
    ManualIncomeForm,
    MarketAssumptionsForm,
    PortfolioForm,
    RiskForm,
    SocialSecurityForm,
    SpendingGoalsForm,
)
from web.routes import (
    EDITOR_HOUSEHOLD,
    EDITOR_JOBS,
    EDITOR_MANUAL_INCOME,
    EDITOR_MARKET_ASSUMPTIONS,
    EDITOR_PORTFOLIO,
    EDITOR_RISK,
    EDITOR_SETTINGS,
    EDITOR_SOCIAL_SECURITY,
    EDITOR_SPENDING,
    HOME,
    PLAN_CREATE,
    PLAN_DELETE,
    PLAN_DUPLICATE,
    PLAN_HOUSEHOLD,
    PLAN_JOBS,
    PLAN_MANUAL_INCOME,
    PLAN_MARKET_ASSUMPTIONS,
    PLAN_PORTFOLIO,
    PLAN_RENAME,
    PLAN_RISK,
    PLAN_SET_DEFAULT,
    PLAN_SETTINGS,
    PLAN_SOCIAL_SECURITY,
    PLAN_SPENDING,
    PLAN_SS_EARNINGS,
    RESULTS,
)
from web.simulation_cache import get_or_run_simulation

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_PACKAGE_DIR / "templates"))
templates.env.globals["routes"] = routes
templates.env.globals["sections"] = sections
templates.env.globals["forms"] = forms
templates.env.globals["boundaries"] = boundaries
templates.env.globals["spending_summary"] = spending_summary
templates.env.filters["usd"] = currency.format_usd
templates.env.filters["percent"] = percent.format_percent

_INIT_DB_MESSAGE = "No database found. Run: uv run python scripts/init_db.py"
_SIMULATION_FAILURE_MESSAGE = "Simulation failed. Check plan inputs and try again."

# A real SSA statement XML is a few hundred KB; cap the upload well above that
# so a malformed or hostile file cannot be read into memory unbounded.
MAX_STATEMENT_BYTES = 5 * 1024 * 1024
STATEMENT_TOO_LARGE_MESSAGE = (
    f"Statement is too large (limit {MAX_STATEMENT_BYTES // (1024 * 1024)} MB)."
)

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


def _error_message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return _validation_message(exc)
    return str(exc)


def _ss_partial(
    request: Request,
    *,
    plan_id: int,
    plan_model: Plan,
    error: str | None = None,
    headers: dict[str, str] | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "editor_social_security.html",
        {"plan_id": plan_id, "plan": plan_model, "ss_error": error},
        headers=headers,
    )


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
            "spending": (
                spending_summary.from_result(result) if result is not None else None
            ),
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

    @web_app.get(EDITOR_JOBS, response_class=HTMLResponse)
    def editor_jobs(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return templates.TemplateResponse(
            request,
            "editor_jobs.html",
            {"plan_id": plan_id, "plan": plan_model},
        )

    @web_app.get(EDITOR_MANUAL_INCOME, response_class=HTMLResponse)
    def editor_manual_income(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return templates.TemplateResponse(
            request,
            "editor_manual_income.html",
            {"plan_id": plan_id, "plan": plan_model},
        )


def _register_spending_routes(web_app: FastAPI) -> None:
    @web_app.get(EDITOR_SPENDING, response_class=HTMLResponse)
    def editor_spending(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return templates.TemplateResponse(
            request,
            "editor_spending.html",
            {"plan_id": plan_id, "plan": plan_model},
        )

    @web_app.patch(PLAN_SPENDING)
    async def patch_spending(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        form = await request.form()
        try:
            updated = SpendingGoalsForm.from_form(
                form,
                today=date.today(),
                existing_essential=plan_model.extra_essential_spending,
                existing_discretionary=plan_model.extra_discretionary_spending,
                existing_legacy_target=plan_model.legacy_target,
            ).apply_to(plan_model)
        except (ValidationError, ValueError, ArithmeticError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)


def _register_risk_routes(web_app: FastAPI) -> None:
    @web_app.get(EDITOR_RISK, response_class=HTMLResponse)
    def editor_risk(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return templates.TemplateResponse(
            request,
            "editor_risk.html",
            {"plan_id": plan_id, "plan": plan_model},
        )

    @web_app.patch(PLAN_RISK)
    def patch_risk(
        risk_tolerance_at_20: Annotated[str, Form()],
        delta_at_max_age: Annotated[str, Form()],
        legacy_delta_from_at_20: Annotated[str, Form()],
        time_preference: Annotated[str, Form()],
        additional_annual_spending_tilt: Annotated[str, Form()],
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        try:
            updated = RiskForm(
                risk_tolerance_at_20=Decimal(risk_tolerance_at_20),
                delta_at_max_age=Decimal(delta_at_max_age),
                legacy_delta_from_at_20=Decimal(legacy_delta_from_at_20),
                time_preference=percent.parse_percent(time_preference),
                additional_annual_spending_tilt=percent.parse_percent(
                    additional_annual_spending_tilt
                ),
            ).apply_to(plan_model)
        except (ValidationError, ValueError, ArithmeticError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)


def _register_market_assumptions_routes(web_app: FastAPI) -> None:
    @web_app.get(EDITOR_MARKET_ASSUMPTIONS, response_class=HTMLResponse)
    def editor_market_assumptions(
        request: Request,
        repo: RepoDep,
        settings_repo: SettingsRepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        settings = settings_repo.get()
        _load_simulation(
            request,
            plan_id=plan_id,
            plan_model=plan_model,
            settings=settings,
        )
        return templates.TemplateResponse(
            request,
            "editor_market_assumptions.html",
            {"plan_id": plan_id, "plan": plan_model},
        )

    @web_app.patch(PLAN_MARKET_ASSUMPTIONS)
    def patch_market_assumptions(
        inflation_mode: Annotated[str, Form()],
        planning_preset: Annotated[str, Form()],
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
        inflation_manual_annual_rate: Annotated[str | None, Form()] = None,
        fixed_equity_premium: Annotated[str | None, Form()] = None,
        custom_stocks_base: Annotated[str | None, Form()] = None,
        custom_bonds_base: Annotated[str | None, Form()] = None,
        custom_stocks_delta: Annotated[str | None, Form()] = None,
        custom_bonds_delta: Annotated[str | None, Form()] = None,
        expected_annual_return_stocks: Annotated[str | None, Form()] = None,
        expected_annual_return_bonds: Annotated[str | None, Form()] = None,
        stock_volatility_scale: Annotated[str | None, Form()] = None,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        try:
            updated = MarketAssumptionsForm.model_validate(
                {
                    "inflation_mode": inflation_mode,
                    "inflation_manual_annual_rate": percent.parse_optional_percent(
                        inflation_manual_annual_rate
                    ),
                    "planning_preset": planning_preset,
                    "fixed_equity_premium": percent.parse_optional_percent(
                        fixed_equity_premium
                    ),
                    "custom_stocks_base": custom_stocks_base or None,
                    "custom_bonds_base": custom_bonds_base or None,
                    "custom_stocks_delta": percent.parse_optional_percent(
                        custom_stocks_delta
                    ),
                    "custom_bonds_delta": percent.parse_optional_percent(
                        custom_bonds_delta
                    ),
                    "expected_annual_return_stocks": percent.parse_optional_percent(
                        expected_annual_return_stocks
                    ),
                    "expected_annual_return_bonds": percent.parse_optional_percent(
                        expected_annual_return_bonds
                    ),
                    "stock_volatility_scale": (
                        Decimal(stock_volatility_scale)
                        if stock_volatility_scale is not None
                        else None
                    ),
                }
            ).apply_to(plan_model)
        except (ValidationError, ValueError, ArithmeticError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)


def _register_social_security_routes(web_app: FastAPI) -> None:
    @web_app.get(EDITOR_SOCIAL_SECURITY, response_class=HTMLResponse)
    def editor_social_security(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return _ss_partial(request, plan_id=plan_id, plan_model=plan_model)

    @web_app.patch(PLAN_SOCIAL_SECURITY)
    def patch_social_security(
        repo: RepoDep,
        claim_age_years: Annotated[int, Form()],
        plan: Annotated[int | None, Query()] = None,
        person: Annotated[str, Query()] = "person1",
        claim_age_months: Annotated[int, Form()] = 0,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        try:
            updated = SocialSecurityForm(
                person=boundaries.parse_person_id(person),
                claim_age_years=claim_age_years,
                claim_age_months=claim_age_months,
            ).apply_to(plan_model)
        except (ValidationError, ValueError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)

    @web_app.post(PLAN_SS_EARNINGS)
    async def upload_ss_earnings(
        request: Request,
        repo: RepoDep,
        statement: UploadFile,
        plan: Annotated[int | None, Query()] = None,
        person: Annotated[str, Query()] = "person1",
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        # Read one byte past the cap so an oversize upload is detectable without
        # materializing the whole body.
        payload = await statement.read(MAX_STATEMENT_BYTES + 1)
        if len(payload) > MAX_STATEMENT_BYTES:
            return _ss_partial(
                request,
                plan_id=plan_id,
                plan_model=plan_model,
                error=STATEMENT_TOO_LARGE_MESSAGE,
            )
        raw = payload.decode("utf-8", errors="replace")
        try:
            person_id = boundaries.parse_person_id(person)
            # ElementTree is deliberate: it does not expand external or nested
            # entities, so a hostile statement cannot mount an XXE or
            # billion-laughs attack. Do not swap in a DTD-processing parser.
            earnings = parse_social_security_statement_xml(raw)
            data = plan_model.household.model_dump()
            if data.get(person_id) is None:
                raise ValueError("No partner on the plan for this upload")
            data[person_id]["social_security"]["earnings_record"] = [
                e.model_dump() for e in earnings
            ]
            household = Household.model_validate(data)
            updated = plan_model.model_copy(update={"household": household})
        except (ValidationError, ValueError) as exc:
            # Returned as 200 so htmx swaps the re-rendered section: it ignores
            # the body of non-2xx responses, which would leave the user with
            # raw markup in the error banner instead of this partial.
            return _ss_partial(
                request,
                plan_id=plan_id,
                plan_model=plan_model,
                error=_error_message(exc),
            )
        repo.save(plan_id, updated)
        return _ss_partial(
            request,
            plan_id=plan_id,
            plan_model=updated,
            headers={"HX-Trigger": "planUpdated"},
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
        ss_pension_taxable_fraction: Annotated[str | None, Form()] = None,
        social_security_trust_factor: Annotated[str | None, Form()] = None,
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
                filing_status=forms.parse_filing_status(filing_status),
                residence_state=residence_state,
                ss_pension_taxable_fraction=percent.parse_optional_percent(
                    ss_pension_taxable_fraction
                ),
                social_security_trust_factor=percent.parse_optional_percent(
                    social_security_trust_factor
                ),
                has_partner=has_partner,
                person2_birth_month=person2_birth_month,
                person2_birth_year=person2_birth_year,
                person2_max_age_years=person2_max_age_years,
            ).apply_to(plan_model)
        except (ValidationError, ValueError, ArithmeticError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)

    @web_app.patch(PLAN_PORTFOLIO)
    def patch_portfolio(
        current_savings_balance: Annotated[str, Form()],
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        try:
            updated = PortfolioForm(
                current_savings_balance=currency.parse_usd(
                    current_savings_balance,
                    previous=plan_model.portfolio.current_savings_balance,
                ),
            ).apply_to(plan_model)
        except (ValidationError, ValueError, ArithmeticError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
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

    @web_app.patch(PLAN_JOBS)
    async def patch_jobs(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
        person: Annotated[str, Query()] = "person1",
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        form = await request.form()
        try:
            person_id = boundaries.parse_person_id(person)
            person_model = getattr(plan_model.household, person_id)
            existing_jobs = [] if person_model is None else list(person_model.jobs)
            updated = JobsForm.from_form(
                form,
                person=person_id,
                today=date.today(),
                existing_jobs=existing_jobs,
            ).apply_to(plan_model)
        except (ValidationError, ValueError, ArithmeticError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)

    @web_app.patch(PLAN_MANUAL_INCOME)
    async def patch_manual_income(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        form = await request.form()
        try:
            updated = ManualIncomeForm.from_form(
                form,
                today=date.today(),
                existing_streams=plan_model.manual_income_streams,
            ).apply_to(plan_model)
        except (ValidationError, ValueError, ArithmeticError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
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
        spending = spending_summary.from_result(result)
        return templates.TemplateResponse(
            request,
            "results.html",
            {
                "plan_id": plan_id,
                "result": result,
                "spending": spending,
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
    _register_spending_routes(web_app)
    _register_risk_routes(web_app)
    _register_market_assumptions_routes(web_app)
    _register_social_security_routes(web_app)
    _register_patch_routes(web_app)
    _register_plan_management_routes(web_app)
    _register_results_route(web_app)

    return web_app


app = create_app()
