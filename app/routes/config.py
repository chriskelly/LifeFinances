"""
Configuration page route handler for LifeFinances app.
"""

import re

import yaml
from flask import Request, flash, redirect, render_template, url_for
from pydantic import ValidationError

from app.models.config import read_config_file, write_config_file


class ConfigPage:
    """
    A class representing the configuration page of the LifeFinances app.

    Attributes:
        template (str): The HTML template for the config page.
    """

    def __init__(self, req: Request):
        self._redirect_to = None
        self._error = None
        if req.method == "POST":
            self._handle_form(req.form)
        self._config = read_config_file()

    @property
    def template(self):
        """Render the config page template or redirect"""
        if self._redirect_to:
            return redirect(url_for(self._redirect_to))
        return render_template("config.html", config=self._config, error=self._error)

    def _handle_form(self, form: dict[str, str]):
        """
        Handle form submission for saving configuration.

        Args:
            form: Form data from the request.
        """
        try:
            write_config_file(form["edited_config"])
            flash("Configuration saved successfully!", "success")
            if "run_simulation" in form:
                # Redirect to run page after saving if run_simulation was clicked
                self._redirect_to = "run"
            else:
                # Redirect back to config page after saving
                self._redirect_to = "config"
        except yaml.YAMLError as error:
            self._error = self._format_yaml_error(error)
            flash("YAML syntax error in configuration", "error")
        except ValidationError as error:
            self._error = self._format_validation_error(error)
            flash("Configuration validation failed", "error")
        except TypeError as error:
            self._error = {
                "type": "Type Error",
                "message": str(error),
                "details": "The configuration file contains invalid data types.",
            }
            flash("Invalid data type in configuration", "error")

    def _format_yaml_error(self, error: yaml.YAMLError) -> dict:
        """
        Format YAML parsing errors into user-friendly messages.

        Args:
            error: YAML parsing error

        Returns:
            Dictionary with error details
        """
        error_str = str(error)
        # Try to extract line number from error message
        line_match = re.search(r"line (\d+)", error_str)
        line_number = line_match.group(1) if line_match else "unknown"

        return {
            "type": "YAML Syntax Error",
            "message": f"Invalid YAML syntax at line {line_number}",
            "details": error_str,
            "suggestion": "Check for incorrect indentation, missing colons, or invalid characters.",
        }

    def _format_validation_error(self, error: ValidationError) -> dict:
        """
        Format Pydantic validation errors into user-friendly messages.

        Args:
            error: Pydantic validation error

        Returns:
            Dictionary with error details
        """
        errors = []
        for err in error.errors():
            # Get the field path (e.g., ["retirement", "flat", "allocation"])
            field_path = " → ".join(str(loc) for loc in err["loc"])
            error_msg = err["msg"]
            error_type = err["type"]

            # Make common errors more user-friendly
            friendly_msg = self._make_error_user_friendly(error_msg, error_type)

            errors.append(
                {
                    "field": field_path,
                    "message": friendly_msg,
                    "original": error_msg,
                }
            )

        return {
            "type": "Validation Error",
            "message": "The configuration contains invalid values",
            "errors": errors,
            "suggestion": "Review the errors below and correct the highlighted fields.",
        }

    def _make_error_user_friendly(self, error_msg: str, error_type: str) -> str:
        """
        Convert technical error messages to user-friendly descriptions.

        Args:
            error_msg: Original error message
            error_type: Pydantic error type

        Returns:
            User-friendly error message
        """
        # Handle specific error patterns
        if "must sum to 1" in error_msg.lower():
            return "All allocation percentages must add up to 100% (sum to 1.0)"

        if "field required" in error_msg.lower():
            return "This field is required and cannot be empty"

        if "not a valid" in error_msg.lower():
            if "integer" in error_msg.lower():
                return "Must be a whole number (integer)"
            if "float" in error_msg.lower():
                return "Must be a decimal number"
            if "boolean" in error_msg.lower():
                return "Must be true or false"

        if error_type == "value_error.missing":
            return "Required field is missing"

        if error_type.startswith("type_error"):
            return "Invalid data type for this field"

        # Return original message if no specific pattern matched
        return error_msg
