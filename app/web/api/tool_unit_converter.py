"""API mixin for unit conversion and dimensional analysis."""
from __future__ import annotations

from typing import Any

from app.features.unit_converter.ops import (
    convert_expression,
    convert_to_compatible_units,
    convert_unit_value,
    get_unit_catalog,
    sanitize_error_message,
)
from app.web.api.result import api_method, ok, require


class UnitConverterApiMixin:
    @api_method
    def units_catalog(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return complete structured unit categories, prefixes, and unit registry.
        data = get_unit_catalog()
        return ok(**data)

    @api_method
    def units_convert(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert numerical value between compatible units with dimensional safety.
        require(params, "from_unit", "to_unit")
        raw_val = params.get("value", 1.0)
        try:
            value = float(raw_val)
        except (ValueError, TypeError):
            value = 0.0

        from_unit = str(params["from_unit"])
        to_unit = str(params["to_unit"])
        fmt_mode = str(params.get("format_mode", params.get("fmt_mode", "standard")))
        sig_figs = int(params.get("sig_figs", 7))

        try:
            res = convert_unit_value(value, from_unit, to_unit, fmt_mode=fmt_mode, sig_figs=sig_figs)
        except Exception as exc:
            raise ValueError(sanitize_error_message(exc)) from exc
        return ok(**res)

    @api_method
    def units_compatible_table(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert value simultaneously across all units in dimension or category.
        require(params, "from_unit")
        raw_val = params.get("value", 1.0)
        try:
            value = float(raw_val)
        except (ValueError, TypeError):
            value = 0.0

        from_unit = str(params["from_unit"])
        category_id = str(params.get("category_id", ""))
        include_all = bool(params.get("include_all", False))
        fmt_mode = str(params.get("format_mode", params.get("fmt_mode", "standard")))
        sig_figs = int(params.get("sig_figs", 7))

        items = convert_to_compatible_units(
            value,
            from_unit,
            category_id=category_id,
            include_all=include_all,
            fmt_mode=fmt_mode,
            sig_figs=sig_figs,
        )
        return ok(items=items, count=len(items))

    @api_method
    def units_expression(self, params: dict[str, Any]) -> dict[str, Any]:
        # Evaluate compound quantity expression and optional target unit conversion.
        require(params, "expression")
        expr_str = str(params["expression"]).strip()
        target_unit = str(params.get("target_unit", "")).strip()
        fmt_mode = str(params.get("format_mode", params.get("fmt_mode", "standard")))
        sig_figs = int(params.get("sig_figs", 7))

        try:
            res = convert_expression(expr_str, target_unit=target_unit, fmt_mode=fmt_mode, sig_figs=sig_figs)
        except Exception as exc:
            raise ValueError(sanitize_error_message(exc)) from exc
        return ok(**res)

