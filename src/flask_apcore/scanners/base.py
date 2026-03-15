"""Base scanner interface and ScannedModule dataclass.

All scanners (NativeFlaskScanner, SmorestScanner, RestxScanner) extend
BaseScanner and produce lists of ScannedModule instances.

ScannedModule keeps Flask-specific fields (http_method, url_rule) as
top-level attributes. The toolkit's domain-agnostic ScannedModule stores
these in metadata instead.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Callable

from apcore import ModuleAnnotations
from apcore_toolkit import BaseScanner as _ToolkitBaseScanner

if TYPE_CHECKING:
    from flask import Flask
    from werkzeug.routing import Rule


@dataclass
class ScannedModule:
    """Result of scanning a single Flask endpoint.

    Attributes:
        module_id: Unique module identifier (e.g., 'users.get_user.get').
        description: Human-readable description for MCP tool listing.
        input_schema: JSON Schema dict for module input.
        output_schema: JSON Schema dict for module output.
        tags: Categorization tags (often derived from Blueprint name).
        target: Callable reference in 'module.path:callable' format.
        http_method: HTTP method (GET, POST, etc.).
        url_rule: The Flask URL rule string.
        version: Module version string.
        annotations: Behavioral annotations inferred from HTTP method.
        documentation: Full docstring text for rich descriptions.
        metadata: Arbitrary key-value data (e.g., scanner source info).
        warnings: Non-fatal issues encountered during scanning.
    """

    module_id: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    tags: list[str]
    target: str
    http_method: str
    url_rule: str
    version: str = "1.0.0"
    annotations: ModuleAnnotations | None = None
    documentation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class BaseScanner(ABC):
    """Abstract base class for all Flask scanners.

    Subclasses must implement scan() and get_source_name().
    Utility methods filter_modules(), _deduplicate_ids(),
    infer_annotations_from_method(), and _is_api_route() are provided
    for common scanner operations.
    """

    @abstractmethod
    def scan(
        self,
        app: Flask,
        include: str | None = None,
        exclude: str | None = None,
    ) -> list[ScannedModule]:
        """Scan Flask app endpoints and return module definitions.

        Args:
            app: Flask application instance (with app context active).
            include: Regex pattern to include (matches against module_id).
            exclude: Regex pattern to exclude (matches against module_id).

        Returns:
            List of ScannedModule instances.
        """
        ...

    @abstractmethod
    def get_source_name(self) -> str:
        """Return human-readable scanner name (e.g., 'native-flask')."""
        ...

    def filter_modules(
        self,
        modules: list[ScannedModule],
        include: str | None = None,
        exclude: str | None = None,
    ) -> list[ScannedModule]:
        """Apply include/exclude regex filters to scanned modules.

        Args:
            modules: List of ScannedModule instances to filter.
            include: If set, only modules whose module_id matches are kept.
            exclude: If set, modules whose module_id matches are removed.

        Returns:
            Filtered list of ScannedModule instances.
        """
        result = modules

        if include is not None:
            pattern = re.compile(include)
            result = [m for m in result if pattern.search(m.module_id)]

        if exclude is not None:
            pattern = re.compile(exclude)
            result = [m for m in result if not pattern.search(m.module_id)]

        return result

    @staticmethod
    def infer_annotations_from_method(method: str) -> ModuleAnnotations:
        """Infer behavioral annotations from an HTTP method.

        Delegates to the shared logic in apcore-toolkit. Mapping:
            GET    -> readonly=True, cacheable=True
            DELETE -> destructive=True
            PUT    -> idempotent=True
            Others -> default (all False)

        Args:
            method: HTTP method string (e.g., "GET", "post").

        Returns:
            ModuleAnnotations instance with inferred flags.
        """
        return _ToolkitBaseScanner.infer_annotations_from_method(method)

    def _deduplicate_ids(self, modules: list[ScannedModule]) -> list[ScannedModule]:
        """Resolve duplicate module IDs by appending _2, _3, etc.

        Unlike django-apcore which deduplicates string IDs,
        this operates on ScannedModule instances directly,
        producing new instances with updated module_id via dataclass replace.
        """
        seen: dict[str, int] = {}
        result: list[ScannedModule] = []
        for module in modules:
            mid = module.module_id
            if mid in seen:
                seen[mid] += 1
                result.append(replace(module, module_id=f"{mid}_{seen[mid]}"))
            else:
                seen[mid] = 1
                result.append(module)
        return result

    def _is_api_route(self, rule: Rule, view_func: Callable) -> bool:
        """Determine if a Flask route is likely an API endpoint.

        Returns False for:
        - Static file routes (endpoint == "static" or "{bp}.static")

        This is a heuristic filter; imprecise but useful for Lite Mode.

        Args:
            rule: werkzeug routing Rule.
            view_func: The view function callable.

        Returns:
            True if the route appears to be an API endpoint.
        """
        if rule.endpoint == "static" or rule.endpoint.endswith(".static"):
            return False
        return True
