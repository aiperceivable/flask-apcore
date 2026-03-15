"""Shared serialization functions for ScannedModule data.

Uses apcore-toolkit's annotations_to_dict for consistent handling.
Flask-specific module_to_dict preserves http_method and url_rule fields.
"""

from __future__ import annotations

from typing import Any

from apcore_toolkit.serializers import annotations_to_dict

from flask_apcore.scanners.base import ScannedModule


def module_to_dict(module: ScannedModule) -> dict[str, Any]:
    """Convert a ScannedModule to a flat dict with all fields.

    The ``annotations`` field is converted to a plain dict via
    ``annotations_to_dict`` when present, or kept as ``None``.

    Args:
        module: A ScannedModule instance.

    Returns:
        Dictionary representation of the module.
    """
    return {
        "module_id": module.module_id,
        "description": module.description,
        "documentation": module.documentation,
        "http_method": module.http_method,
        "url_rule": module.url_rule,
        "tags": module.tags,
        "version": module.version,
        "target": module.target,
        "annotations": annotations_to_dict(module.annotations),
        "metadata": module.metadata,
        "input_schema": module.input_schema,
        "output_schema": module.output_schema,
    }


def modules_to_dicts(modules: list[ScannedModule]) -> list[dict[str, Any]]:
    """Batch-convert a list of ScannedModules to dicts.

    Args:
        modules: List of ScannedModule instances.

    Returns:
        List of dictionary representations.
    """
    return [module_to_dict(m) for m in modules]


__all__ = ["annotations_to_dict", "module_to_dict", "modules_to_dicts"]
