"""JSON API endpoints under ``/api``."""

import json
from typing import Any

import yaml
from flask import Blueprint, request
from pydantic import ValidationError

from app.models.config.utils import read_config_file, write_config_file
from app.models.simulator import gen_simulation_results
from app.routes.api_json import json_error, json_success

api = Blueprint("api", __name__)


@api.route("/config", methods=["GET"])
def get_config_route() -> tuple[Any, int]:
    """Return the active configuration file as raw YAML text."""
    content = read_config_file()
    return json_success({"content": content})


@api.route("/config", methods=["PUT"])
def put_config_route() -> tuple[Any, int]:
    """Validate and persist configuration YAML from the request body."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "content" not in payload:
        return json_error(
            message="Request body must be a JSON object with a string 'content' field.",
            status=400,
            code="validation_error",
        )
    content = payload["content"]
    if not isinstance(content, str):
        return json_error(
            message="Field 'content' must be a string.",
            status=400,
            code="validation_error",
        )
    try:
        write_config_file(content)
    except (yaml.YAMLError, TypeError) as error:
        return json_error(
            message="Invalid YAML.",
            status=400,
            code="validation_error",
            details=str(error),
        )
    except ValidationError as error:
        return json_error(
            message="Configuration does not match the required schema.",
            status=400,
            code="validation_error",
            details=str(error),
        )
    return json_success({"ok": True, "message": "Configuration saved"})


@api.route("/simulation/run", methods=["POST"])
def run_simulation_route() -> tuple[Any, int]:
    """Run the simulation against the persisted config file and return summary JSON."""
    try:
        results = gen_simulation_results()
    except (yaml.YAMLError, TypeError, ValidationError) as error:
        return json_error(
            message="Invalid or unreadable configuration for simulation.",
            status=400,
            code="validation_error",
            details=str(error),
        )
    except Exception as error:
        return json_error(
            message="Simulation failed.",
            status=500,
            code="simulation_error",
            details=str(error),
        )
    first_df = results.as_dataframes()[0]
    split_json = first_df.to_json(orient="split")
    if split_json is None:
        return json_error(
            message="Simulation output could not be serialized.",
            status=500,
            code="simulation_error",
        )
    split = json.loads(split_json)
    first_result = {"columns": split["columns"], "data": split["data"]}
    return json_success(
        {
            "success_percentage": results.calc_success_percentage(),
            "first_result": first_result,
        }
    )
