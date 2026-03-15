"""Flask Extension for apcore AI-Perceivable Core integration.

Provides the Apcore class as a unified entry point following Flask's
Extension pattern. All apcore components (Registry, Executor, Context,
Observability, Events, System Modules) are accessible via properties.

init_app flow:
1. load_settings(app)
2. Create Registry
3. Create ExtensionManager, register event listeners
4. Call setup_observability(settings, ext_data)
5. Register CLI commands
6. Auto-discover if enabled (load bindings + scan packages)
7. Register system modules if enabled
8. Store everything in app.extensions["apcore"]
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask import Flask

from flask_apcore.config import load_settings
from flask_apcore.observability import setup_observability
from flask_apcore.registry import get_executor, get_registry

logger = logging.getLogger("flask_apcore")


def _get_ext_data(app: Any = None) -> dict[str, Any]:
    """Get app.extensions['apcore'] with validation."""
    if app is None:
        from flask import current_app

        app = current_app._get_current_object()
    ext_data = app.extensions.get("apcore")
    if ext_data is None:
        raise RuntimeError("flask-apcore not initialized. Call Apcore(app) or apcore.init_app(app) first.")
    return ext_data


class Apcore:
    """Flask Extension for apcore — unified entry point.

    Provides property-based access to all apcore components and
    convenience methods for common operations.

    Usage (direct)::

        app = Flask(__name__)
        apcore = Apcore(app)

        # Access components via properties
        apcore.registry      # -> Registry
        apcore.executor      # -> Executor (lazy)
        apcore.settings      # -> ApcoreSettings
        apcore.metrics       # -> MetricsCollector | None
        apcore.events        # -> EventEmitter | None
        apcore.error_history # -> ErrorHistory | None

        # Convenience methods
        apcore.call("module.id", {"key": "value"})
        apcore.validate("module.id", {"key": "value"})
        apcore.list_modules()

    Usage (factory pattern)::

        apcore = Apcore()

        def create_app():
            app = Flask(__name__)
            apcore.init_app(app)
            return app
    """

    def __init__(self, app: Flask | None = None) -> None:
        """Initialize the extension.

        Args:
            app: Flask application instance. If provided, init_app()
                 is called immediately.
        """
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize the extension with a Flask application.

        This method:
        1. Validates APCORE_* configuration in app.config
        2. Creates the app-scoped Registry singleton
        3. Creates ExtensionManager and registers event listeners
        4. Sets up observability (tracing, metrics, logging)
        5. Registers the Click CLI command group
        6. If APCORE_AUTO_DISCOVER is True:
           a. Loads YAML binding files from APCORE_MODULE_DIR
           b. Scans for @module-decorated functions in configured packages
        7. Registers system modules if APCORE_SYS_MODULES_ENABLED is True
        8. Stores everything in app.extensions["apcore"]

        Args:
            app: Flask application instance.

        Raises:
            ValueError: If any APCORE_* config value is invalid.
        """
        # 1. Load and validate config
        settings = load_settings(app)

        # 2. Create Registry
        from apcore import Registry

        registry = Registry()

        # 3. Create ExtensionManager
        from apcore import ExtensionManager

        ext_mgr = ExtensionManager()

        # 4. Set up observability — populates ext_data with middlewares
        ext_data: dict[str, Any] = {
            "registry": registry,
            "executor": None,  # Lazily created by get_executor()
            "settings": settings,
            "extension_manager": ext_mgr,
        }
        setup_observability(settings, ext_data)

        # Store in app.extensions
        app.extensions["apcore"] = ext_data

        # 5. Register CLI commands
        from flask_apcore.cli import apcore_cli

        app.cli.add_command(apcore_cli)

        logger.debug("flask-apcore initialized for app %s", app.name)

        # 6. Auto-discover if enabled
        if settings.auto_discover:
            self._register_event_listeners(registry)

            # 6a. Load YAML binding files
            module_dir = Path(settings.module_dir)
            if module_dir.exists() and module_dir.is_dir():
                self._load_bindings(registry, str(module_dir), settings.binding_pattern)
            else:
                logger.warning(
                    "Module directory not found: %s. " "Skipping auto-discovery of binding files.",
                    module_dir,
                )

            # 6b. Scan packages for @module-decorated functions
            if settings.module_packages:
                self._scan_packages_for_modules(registry, settings.module_packages)

            # 6c. Flatten Pydantic model params for all registered modules
            self._flatten_registered_modules(registry)

            logger.info(
                "flask-apcore: auto-discovery complete: %d total modules",
                registry.count,
            )
        else:
            logger.debug("Auto-discovery disabled (APCORE_AUTO_DISCOVER=False)")

        # 7. Register system modules if enabled
        if settings.sys_modules_enabled:
            self._register_sys_modules(ext_data, settings)

    # -----------------------------------------------------------------------
    # Properties — unified access to all components
    # -----------------------------------------------------------------------

    @property
    def registry(self) -> Any:
        """The apcore Registry for the current app."""
        return get_registry()

    @property
    def executor(self) -> Any:
        """The apcore Executor for the current app (lazily created)."""
        return get_executor()

    @property
    def settings(self) -> Any:
        """The validated ApcoreSettings for the current app."""
        return _get_ext_data()["settings"]

    @property
    def metrics(self) -> Any:
        """The MetricsCollector, or None if metrics disabled."""
        return _get_ext_data().get("metrics_collector")

    @property
    def error_history(self) -> Any:
        """The ErrorHistory, or None if observability disabled."""
        return _get_ext_data().get("error_history")

    @property
    def usage(self) -> Any:
        """The UsageCollector, or None if metrics disabled."""
        return _get_ext_data().get("usage_collector")

    @property
    def events(self) -> Any:
        """The EventEmitter, or None if events disabled."""
        return _get_ext_data().get("event_emitter")

    @property
    def extension_manager(self) -> Any:
        """The apcore ExtensionManager."""
        return _get_ext_data()["extension_manager"]

    # -----------------------------------------------------------------------
    # Convenience methods — delegate to Executor
    # -----------------------------------------------------------------------

    def call(self, module_id: str, inputs: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """Execute a module synchronously.

        Args:
            module_id: The module to call.
            inputs: Input arguments dict.
            **kwargs: Additional arguments passed to Executor.call().

        Returns:
            Module output dict.
        """
        return self.executor.call(module_id, inputs or {}, **kwargs)

    def validate(self, module_id: str, inputs: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Preflight validation without execution.

        Args:
            module_id: The module to validate.
            inputs: Input arguments dict.
            **kwargs: Additional arguments passed to Executor.validate().

        Returns:
            PreflightResult with per-check details.
        """
        return self.executor.validate(module_id, inputs or {}, **kwargs)

    def list_modules(self, tags: list[str] | None = None, prefix: str | None = None) -> list[str]:
        """List registered module IDs with optional filtering.

        Args:
            tags: Filter by tags (modules must have at least one matching tag).
            prefix: Filter by module ID prefix.

        Returns:
            List of matching module IDs.
        """
        return self.registry.list(tags=tags, prefix=prefix)

    def describe(self, module_id: str) -> str:
        """Get human-readable description of a module.

        Args:
            module_id: The module to describe.

        Returns:
            Description string.
        """
        return self.registry.describe(module_id)

    # -----------------------------------------------------------------------
    # Legacy accessors (backward compat)
    # -----------------------------------------------------------------------

    def get_registry(self, app: Flask | None = None) -> Any:
        """Return the apcore Registry for the given app.

        Args:
            app: Flask app instance. If None, uses current_app.

        Returns:
            The apcore Registry scoped to this app.
        """
        return get_registry(app)

    def get_executor(self, app: Flask | None = None) -> Any:
        """Return the apcore Executor for the given app.

        Args:
            app: Flask app instance. If None, uses current_app.

        Returns:
            The apcore Executor scoped to this app.
        """
        return get_executor(app)

    # -----------------------------------------------------------------------
    # Private init helpers
    # -----------------------------------------------------------------------

    def _register_event_listeners(self, registry: Any) -> None:
        """Register event listeners on the registry for debug logging."""
        try:
            registry.on(
                "register",
                lambda module_id, module: logger.debug("Registry event: registered module '%s'", module_id),
            )
            logger.debug("Registered event listeners on registry")
        except (AttributeError, TypeError):
            logger.debug("Registry does not support events; skipping event listener registration")

    def _flatten_registered_modules(self, registry: Any) -> None:
        """Re-register modules whose functions have Pydantic model parameters."""
        from apcore_toolkit import flatten_pydantic_params as _flatten_pydantic_params

        for module_id in list(registry.module_ids):
            module = registry.get(module_id)
            func = getattr(module, "_func", None)
            if func is None:
                continue
            wrapped = _flatten_pydantic_params(func)
            if wrapped is func:
                continue

            from apcore import FunctionModule

            new_module = FunctionModule(
                func=wrapped,
                module_id=module.module_id,
                description=module.description,
                documentation=getattr(module, "documentation", None),
                tags=getattr(module, "tags", None),
                version=getattr(module, "version", "1.0.0"),
                annotations=getattr(module, "annotations", None),
                metadata=getattr(module, "metadata", None),
            )
            registry.unregister(module_id)
            registry.register(module_id, new_module)
            logger.debug("Flattened Pydantic params for module: %s", module_id)

    def _load_bindings(self, registry: Any, module_dir: str, pattern: str) -> None:
        """Load YAML binding files from the module directory."""
        try:
            from apcore import BindingLoader

            loader = BindingLoader()
            modules = loader.load_binding_dir(str(module_dir), registry, pattern=pattern)
            count = len(modules) if modules else 0
            logger.info("Loaded %d binding modules from %s", count, module_dir)
        except ImportError:
            logger.warning("apcore.BindingLoader not available; skipping binding file loading")
        except Exception:
            logger.exception("Error loading binding files from %s", module_dir)

    def _scan_packages_for_modules(self, registry: Any, packages: list[str]) -> None:
        """Scan Python packages for @module-decorated functions."""
        for package_name in packages:
            try:
                mod = importlib.import_module(package_name)
                for attr_name in dir(mod):
                    obj = getattr(mod, attr_name)
                    if callable(obj) and hasattr(obj, "apcore_module"):
                        try:
                            fm = obj.apcore_module
                            registry.register(fm.module_id, fm)
                            logger.debug(
                                "Registered @module function: %s.%s",
                                package_name,
                                attr_name,
                            )
                        except Exception:
                            logger.warning(
                                "Failed to register module from %s.%s",
                                package_name,
                                attr_name,
                                exc_info=True,
                            )
            except ImportError:
                logger.debug(
                    "Package %s not found; skipping module scan",
                    package_name,
                )
            except Exception:
                logger.warning(
                    "Error scanning %s for apcore modules",
                    package_name,
                    exc_info=True,
                )

    def _register_sys_modules(self, ext_data: dict[str, Any], settings: Any) -> None:
        """Register apcore system modules (health, manifest, usage, control)."""
        try:
            from apcore import Config, register_sys_modules

            registry = ext_data["registry"]

            executor = ext_data.get("executor")
            if executor is None:
                from apcore import Executor

                obs_middlewares = ext_data.get("observability_middlewares", [])
                executor = Executor(registry, middlewares=obs_middlewares)
                ext_data["executor"] = executor

            config_data: dict[str, Any] = {
                "sys_modules": {
                    "enabled": True,
                    "events": {
                        "enabled": settings.sys_modules_events_enabled,
                    },
                },
            }
            config = Config(data=config_data)
            metrics_collector = ext_data.get("metrics_collector")

            context = register_sys_modules(
                registry=registry,
                executor=executor,
                config=config,
                metrics_collector=metrics_collector,
            )
            ext_data["sys_modules_context"] = context

            logger.info(
                "flask-apcore: system modules registered (%d modules)",
                sum(1 for mid in registry.module_ids if mid.startswith("system.")),
            )
        except ImportError:
            logger.warning("apcore.register_sys_modules not available; upgrade to apcore>=0.11.0 for system modules")
        except Exception:
            logger.exception("Error registering system modules")
