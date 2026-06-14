from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Annotated

from core.paths import default_db_path
from core.repository import PlanRepository
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from simulation.stub import run_simulation

from web import forms, routes, sections
from web.dependencies import get_repository
from web.forms import HouseholdForm, PortfolioForm
from web.routes import (
    EDITOR_HOUSEHOLD,
    EDITOR_PORTFOLIO,
    HOME,
    PLAN_HOUSEHOLD,
    PLAN_PORTFOLIO,
    RESULTS,
)

_PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_PACKAGE_DIR / "templates"))
templates.env.globals["routes"] = routes
templates.env.globals["sections"] = sections
templates.env.globals["forms"] = forms

_INIT_DB_MESSAGE = "No database found. Run: uv run python scripts/init_db.py"


def _resolve_db_path(app: FastAPI) -> Path:
    db_path = app.state.db_path
    if db_path is None:
        return default_db_path()
    return db_path


def get_repo(request: Request) -> PlanRepository:
    return get_repository(_resolve_db_path(request.app))


RepoDep = Annotated[PlanRepository, Depends(get_repo)]


def create_app(*, db_path: Path | None = None) -> FastAPI:
    app = FastAPI()
    app.state.db_path = db_path

    app.mount(
        routes.STATIC,
        StaticFiles(directory=_PACKAGE_DIR / "static"),
        name="static",
    )

    @app.get(HOME, response_class=HTMLResponse)
    def home(
        request: Request,
        repo: RepoDep,
    ) -> HTMLResponse:
        resolved_db_path = _resolve_db_path(request.app)
        if not resolved_db_path.exists():
            return templates.TemplateResponse(
                request,
                "error.html",
                {"message": _INIT_DB_MESSAGE},
            )

        _, plan = repo.get_or_create_default()
        result = run_simulation(plan)
        return templates.TemplateResponse(
            request,
            "index.html",
            {"plan": plan, "result": result},
        )

    @app.get(EDITOR_HOUSEHOLD, response_class=HTMLResponse)
    def editor_household(
        request: Request,
        repo: RepoDep,
    ) -> HTMLResponse:
        _, plan = repo.get_or_create_default()
        return templates.TemplateResponse(
            request,
            "editor_household.html",
            {"plan": plan},
        )

    @app.get(EDITOR_PORTFOLIO, response_class=HTMLResponse)
    def editor_portfolio(
        request: Request,
        repo: RepoDep,
    ) -> HTMLResponse:
        _, plan = repo.get_or_create_default()
        return templates.TemplateResponse(
            request,
            "editor_portfolio.html",
            {"plan": plan},
        )

    @app.patch(PLAN_HOUSEHOLD)
    def patch_household(
        person1_birth_month: Annotated[int, Form()],
        person1_birth_year: Annotated[int, Form()],
        person1_max_age_years: Annotated[int, Form()],
        person2_birth_month: Annotated[int, Form()],
        person2_birth_year: Annotated[int, Form()],
        person2_max_age_years: Annotated[int, Form()],
        repo: RepoDep,
    ) -> Response:
        plan_id, plan = repo.get_or_create_default()
        updated = HouseholdForm(
            person1_birth_month=person1_birth_month,
            person1_birth_year=person1_birth_year,
            person1_max_age_years=person1_max_age_years,
            person2_birth_month=person2_birth_month,
            person2_birth_year=person2_birth_year,
            person2_max_age_years=person2_max_age_years,
        ).apply_to(plan)
        repo.save(plan_id, updated)
        return Response(status_code=200)

    @app.patch(PLAN_PORTFOLIO)
    def patch_portfolio(
        current_savings_balance: Annotated[Decimal, Form()],
        repo: RepoDep,
    ) -> Response:
        plan_id, plan = repo.get_or_create_default()
        updated = PortfolioForm(
            current_savings_balance=current_savings_balance,
        ).apply_to(plan)
        repo.save(plan_id, updated)
        return Response(status_code=200)

    @app.get(RESULTS, response_class=HTMLResponse)
    def results(
        request: Request,
        repo: RepoDep,
    ) -> HTMLResponse:
        _, plan = repo.get_or_create_default()
        result = run_simulation(plan)
        return templates.TemplateResponse(
            request,
            "results_stub.html",
            {"result": result},
        )

    return app


app = create_app()
