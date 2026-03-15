"""Registry writer for direct module registration.

Converts ScannedModule instances into apcore FunctionModule instances
and registers them directly into an apcore Registry. This is the default
output mode (no file I/O needed).

Uses apcore-toolkit's flatten_pydantic_params and resolve_target utilities.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from apcore_toolkit import flatten_pydantic_params, resolve_target
from apcore_toolkit.output.types import WriteResult
from apcore_toolkit.serializers import annotations_to_dict

if TYPE_CHECKING:
    from apcore import Registry

    from flask_apcore.scanners.base import ScannedModule

logger = logging.getLogger("flask_apcore")


class RegistryWriter:
    """Converts ScannedModule to FunctionModule and registers into Registry.

    This is the default writer used when no output_format is specified.
    Instead of writing YAML binding files, it registers modules directly
    into the apcore Registry for immediate use.
    """

    def write(
        self,
        modules: list[ScannedModule],
        registry: Registry,
        *,
        dry_run: bool = False,
    ) -> list[WriteResult]:
        """Register scanned modules into the registry.

        Args:
            modules: List of ScannedModule instances to register.
            registry: The apcore Registry to register modules into.
            dry_run: If True, skip registration and return results only.

        Returns:
            List of WriteResult instances.
        """
        results: list[WriteResult] = []
        for mod in modules:
            if dry_run:
                results.append(WriteResult(module_id=mod.module_id))
                continue
            fm = self._to_function_module(mod)
            registry.register(mod.module_id, fm)
            results.append(WriteResult(module_id=mod.module_id))
            logger.debug("Registered module: %s", mod.module_id)
        return results

    def _to_function_module(self, mod: ScannedModule) -> Any:
        """Convert a ScannedModule to an apcore FunctionModule.

        Args:
            mod: The ScannedModule to convert.

        Returns:
            A FunctionModule instance ready for registry insertion.
        """
        from apcore import FunctionModule

        func = flatten_pydantic_params(resolve_target(mod.target))

        metadata = {
            **(mod.metadata or {}),
            "http_method": mod.http_method,
            "url_rule": mod.url_rule,
        }

        return FunctionModule(
            func=func,
            module_id=mod.module_id,
            description=mod.description,
            documentation=mod.documentation,
            tags=mod.tags,
            version=mod.version,
            annotations=annotations_to_dict(mod.annotations),
            metadata=metadata,
        )
