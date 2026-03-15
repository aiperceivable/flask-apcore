"""flask-apcore: Flask Extension for apcore AI-Perceivable Core integration."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version

from flask_apcore.extension import Apcore

from apcore import module

from apcore import (
    ACL,
    Config,
    Context,
    Executor,
    Identity,
    Middleware,
    ModuleAnnotations,
    ModuleDescriptor,
    Registry,
    # Approval system (0.7.0+)
    ApprovalHandler,
    AutoApproveHandler,
    AlwaysDenyHandler,
    # Cancellation (0.8.0+)
    CancelToken,
    # Events (0.11.0+)
    EventEmitter,
    EventSubscriber,
    ApCoreEvent,
    # Preflight (0.9.0+)
    PreflightResult,
    # Module types
    FunctionModule,
    ModuleExample,
    # Errors
    ModuleError,
    ModuleNotFoundError,
    ACLDeniedError,
    SchemaValidationError,
    InvalidInputError,
    # System modules (0.11.0+)
    register_sys_modules,
)


try:
    __version__ = _get_version("flask-apcore")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "Apcore",
    "__version__",
    "module",
    "ACL",
    "Config",
    "Context",
    "Executor",
    "Identity",
    "Middleware",
    "ModuleAnnotations",
    "ModuleDescriptor",
    "Registry",
    # Approval system
    "ApprovalHandler",
    "AutoApproveHandler",
    "AlwaysDenyHandler",
    # Cancellation
    "CancelToken",
    # Events
    "EventEmitter",
    "EventSubscriber",
    "ApCoreEvent",
    # Preflight
    "PreflightResult",
    # Module types
    "FunctionModule",
    "ModuleExample",
    # Errors
    "ModuleError",
    "ModuleNotFoundError",
    "ACLDeniedError",
    "SchemaValidationError",
    "InvalidInputError",
    # System modules
    "register_sys_modules",
]
