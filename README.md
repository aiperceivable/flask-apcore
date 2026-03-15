# flask-apcore

Flask Extension for [apcore](https://github.com/aipartnerup/apcore-python) (AI-Perceivable Core) integration. Expose your Flask routes as MCP tools with auto-discovery, Pydantic schema inference, and built-in observability.

## Features

- **Route scanning** -- auto-discover Flask routes and convert them to apcore modules
- **Annotation inference** -- `GET` -> readonly+cacheable, `DELETE` -> destructive, `PUT` -> idempotent
- **Pydantic schema inference** -- input/output schemas extracted from type hints automatically
- **Docstring enrichment** -- parameter descriptions from docstrings injected into JSON Schema
- **`@module` decorator** -- define standalone AI-callable modules with full schema enforcement
- **YAML binding** -- zero-code module definitions via external `.binding.yaml` files
- **Python output** -- generate `@module`-decorated Python files from scanned routes
- **MCP server** -- stdio and streamable-http transports via `flask apcore serve`
- **Observability** -- distributed tracing, metrics, structured logging, error history, usage tracking
- **System modules** -- built-in health, manifest, usage, and control modules (apcore 0.11.0+)
- **Input validation** -- validate tool inputs against Pydantic schemas before execution
- **CLI-first workflow** -- `flask apcore scan` + `flask apcore serve` for zero-intrusion integration
- **MCP Tool Explorer** -- browser UI for inspecting modules via `flask apcore serve --explorer`
- **JWT authentication** -- protect MCP endpoints with Bearer tokens via `--jwt-secret`
- **Approval system** -- require approval for destructive operations via `--approval`
- **AI enhancement** -- enrich module metadata using local SLMs via `--ai-enhance`
- **Unified entry point** -- `Apcore` class provides property-based access to all components

## Requirements

- Python >= 3.11
- Flask >= 3.0
- apcore >= 0.13.0
- apcore-toolkit >= 0.2.0

## Installation

```bash
# Core
pip install flask-apcore

# With MCP server support (required for `flask apcore serve`)
pip install flask-apcore[mcp]

# All optional extras
pip install flask-apcore[mcp,smorest,restx]
```

## Quick Start

### 1. Add Apcore to your Flask app

```python
from flask import Flask
from flask_apcore import Apcore

app = Flask(__name__)
apcore = Apcore(app)

@app.route("/greet/<name>", methods=["GET"])
def greet(name: str) -> dict:
    """Greet a user by name."""
    return {"message": f"Hello, {name}!"}
```

Or use the **factory pattern**:

```python
from flask import Flask
from flask_apcore import Apcore

apcore = Apcore()

def create_app():
    app = Flask(__name__)
    # ... register routes / blueprints ...
    apcore.init_app(app)
    return app
```

### 2. Scan routes and start MCP server

```bash
export FLASK_APP=app.py

# Scan Flask routes -> register as apcore modules
flask apcore scan

# Start MCP server (stdio, for Claude Desktop / Cursor)
flask apcore serve
```

That's it. Your Flask routes are now MCP tools.

### 3. Unified entry point

The `Apcore` instance provides property-based access to all components:

```python
apcore = Apcore(app)

with app.app_context():
    # Properties
    apcore.registry           # Registry
    apcore.executor           # Executor (lazy-created)
    apcore.settings           # ApcoreSettings
    apcore.metrics            # MetricsCollector | None
    apcore.events             # EventEmitter | None
    apcore.error_history      # ErrorHistory | None
    apcore.usage              # UsageCollector | None

    # Convenience methods
    apcore.call("task_stats.v1")
    apcore.validate("task_stats.v1", {"key": "value"})
    apcore.list_modules(tags=["api"])
    apcore.describe("task_stats.v1")
```

### 4. Connect an MCP client

For **Claude Desktop**, add to your config:

```json
{
  "mcpServers": {
    "my-flask-app": {
      "command": "flask",
      "args": ["apcore", "serve"],
      "env": { "FLASK_APP": "app.py" }
    }
  }
}
```

For **HTTP transport** (remote access):

```bash
flask apcore serve --http --host 0.0.0.0 --port 9100
```

## Integration Paths

flask-apcore supports three ways to define AI-perceivable modules:

### Route Scanning (zero-intrusion)

Scan existing Flask routes without modifying any code:

```bash
# Direct registration (in-memory)
flask apcore scan

# Generate YAML binding files (persistent)
flask apcore scan --output yaml --dir ./apcore_modules

# Generate Python module files
flask apcore scan --output python --dir ./apcore_modules

# Preview without side effects
flask apcore scan --dry-run

# Filter routes by regex
flask apcore scan --include "user.*" --exclude ".*delete"

# AI-enhanced module descriptions (requires APCORE_AI_ENABLED)
flask apcore scan --ai-enhance

# Verify written output
flask apcore scan --output yaml --verify
```

### `@module` Decorator (precise control)

Define standalone modules with full schema enforcement:

```python
from flask_apcore import Apcore, module
from pydantic import BaseModel

class SummaryResult(BaseModel):
    total: int
    active: int

@module(id="user_stats.v1", tags=["analytics"])
def user_stats() -> SummaryResult:
    """Return user statistics."""
    return SummaryResult(total=100, active=42)

app = Flask(__name__)
app.config["APCORE_MODULE_PACKAGES"] = ["myapp.modules"]
Apcore(app)
```

### YAML Binding (zero-code)

Define modules externally in `.binding.yaml` files:

```yaml
# apcore_modules/greet.binding.yaml
bindings:
  - module_id: greet.get
    target: app.greet
    description: "Greet a user by name"
```

Set `APCORE_AUTO_DISCOVER=True` (default) to load bindings on startup.

## CLI Commands

### `flask apcore scan`

Scan Flask routes and generate apcore module definitions.

```
Options:
  -s, --source [auto|native|smorest|restx]  Scanner source (default: auto)
  -o, --output [yaml|python]                Output format; omit for direct registration
  -d, --dir PATH                            Output directory (default: APCORE_MODULE_DIR)
  --dry-run                                 Preview without writing or registering
  --include REGEX                           Only include matching module IDs
  --exclude REGEX                           Exclude matching module IDs
  --ai-enhance                              AI-enhance module metadata (requires APCORE_AI_ENABLED)
  --verify                                  Verify written output
```

### `flask apcore serve`

Start an MCP server exposing registered modules as tools.

```
Options:
  --stdio                  Use stdio transport (default)
  --http                   Use streamable-http transport
  --host TEXT              HTTP host (default: 127.0.0.1)
  -p, --port INT           HTTP port (default: 9100)
  --name TEXT              MCP server name (default: apcore-mcp)
  --validate-inputs        Validate tool inputs against schemas
  --log-level [DEBUG|INFO|WARNING|ERROR]

  Module Filtering:
  --tags TEXT              Comma-separated tags to filter modules
  --prefix TEXT            Module ID prefix filter

  Explorer:
  --explorer               Enable the MCP Tool Explorer UI
  --explorer-prefix TEXT   URL prefix for explorer (default: /explorer)
  --allow-execute          Allow Try-it execution in the explorer
  --explorer-title TEXT    Page title for Explorer UI
  --explorer-project-name  Project name shown in Explorer footer
  --explorer-project-url   Project URL shown in Explorer footer

  Authentication:
  --jwt-secret TEXT        JWT secret key for MCP auth (HTTP only)
  --jwt-algorithm ALGO     JWT signing algorithm (default: HS256)
  --jwt-audience TEXT      Expected JWT audience claim
  --jwt-issuer TEXT        Expected JWT issuer claim
  --require-auth/--no-require-auth  Require auth for all requests (default: True)
  --exempt-paths TEXT      Comma-separated paths exempt from auth

  Execution:
  --approval [off|elicit|auto-approve|always-deny]  Approval mode (default: off)
  --output-formatter TEXT  Output formatter dotted path (e.g., apcore_toolkit.to_markdown)
```

## Configuration

All settings use the `APCORE_` prefix in `app.config`:

```python
app.config.update(
    # Core
    APCORE_AUTO_DISCOVER=True,          # Auto-load bindings and @module packages
    APCORE_MODULE_DIR="apcore_modules/",# Directory for binding files
    APCORE_BINDING_PATTERN="*.binding.yaml",  # Glob pattern for binding files
    APCORE_MODULE_PACKAGES=[],          # Python packages to scan for @module functions
    APCORE_SCANNER_SOURCE="auto",       # Scanner: auto, native, smorest, restx

    # System Modules (apcore 0.11.0+)
    APCORE_SYS_MODULES_ENABLED=False,   # Enable system modules (health, manifest, usage, control)
    APCORE_SYS_MODULES_EVENTS_ENABLED=False,  # Enable event system for platform notifications

    # Middleware & Execution
    APCORE_MIDDLEWARES=[],              # Middleware dotted paths (e.g. ["myapp.mw.AuthMW"])
    APCORE_ACL_PATH=None,              # ACL file path (e.g. "acl.yaml")
    APCORE_CONTEXT_FACTORY=None,       # Custom ContextFactory dotted path
    APCORE_EXECUTOR_CONFIG=None,       # Executor config dict (passed to apcore.Config)
    APCORE_EXTENSIONS=[],              # Extension plugin dotted paths

    # MCP Server
    APCORE_SERVE_TRANSPORT="stdio",     # Transport: stdio, streamable-http, sse
    APCORE_SERVE_HOST="127.0.0.1",      # HTTP host
    APCORE_SERVE_PORT=9100,             # HTTP port
    APCORE_SERVER_NAME="apcore-mcp",    # MCP server name
    APCORE_SERVER_VERSION=None,         # MCP server version string
    APCORE_SERVE_VALIDATE_INPUTS=False, # Validate inputs against schemas
    APCORE_SERVE_LOG_LEVEL=None,        # Log level: DEBUG, INFO, WARNING, ERROR
    APCORE_SERVE_TAGS=None,             # Filter modules by tags (list of strings)
    APCORE_SERVE_PREFIX=None,           # Filter modules by ID prefix

    # MCP Authentication
    APCORE_SERVE_JWT_SECRET=None,            # JWT secret key (enables auth when set)
    APCORE_SERVE_JWT_ALGORITHM="HS256",      # Signing algorithm
    APCORE_SERVE_JWT_AUDIENCE=None,          # Expected audience claim
    APCORE_SERVE_JWT_ISSUER=None,            # Expected issuer claim
    APCORE_SERVE_REQUIRE_AUTH=True,          # Require auth for all requests
    APCORE_SERVE_EXEMPT_PATHS=None,          # Paths exempt from auth (list of strings)

    # MCP Approval (apcore-mcp 0.8.0+)
    APCORE_SERVE_APPROVAL="off",             # Approval mode: off, elicit, auto-approve, always-deny
    APCORE_SERVE_OUTPUT_FORMATTER=None,      # Output formatter dotted path

    # MCP Tool Explorer
    APCORE_SERVE_EXPLORER=False,             # Enable Tool Explorer UI in MCP server
    APCORE_SERVE_EXPLORER_PREFIX="/explorer",# URL prefix for explorer
    APCORE_SERVE_ALLOW_EXECUTE=False,        # Allow Try-it execution in explorer
    APCORE_SERVE_EXPLORER_TITLE="MCP Tool Explorer",  # Explorer page title
    APCORE_SERVE_EXPLORER_PROJECT_NAME=None, # Project name in explorer footer
    APCORE_SERVE_EXPLORER_PROJECT_URL=None,  # Project URL in explorer footer

    # Observability
    APCORE_TRACING_ENABLED=False,       # Enable distributed tracing
    APCORE_TRACING_EXPORTER="stdout",   # Exporter: stdout, memory, otlp
    APCORE_TRACING_OTLP_ENDPOINT=None,  # OTLP collector URL (e.g. "http://localhost:4317")
    APCORE_TRACING_SERVICE_NAME="flask-apcore",  # Service name for traces
    APCORE_METRICS_ENABLED=False,       # Enable metrics collection
    APCORE_METRICS_BUCKETS=None,        # Custom histogram buckets (list of floats)
    APCORE_LOGGING_ENABLED=False,       # Enable structured logging
    APCORE_LOGGING_FORMAT="json",       # Format: json, text
    APCORE_LOGGING_LEVEL="INFO",        # Level: trace, debug, info, warn, error, fatal

    # Scan Options
    APCORE_SCAN_AI_ENHANCE=False,       # AI-enhance scanned modules (requires APCORE_AI_ENABLED)
    APCORE_SCAN_VERIFY=False,           # Verify written output by default
)
```

## Observability

Enable tracing, metrics, and structured logging:

```python
app.config.update(
    APCORE_TRACING_ENABLED=True,
    APCORE_TRACING_EXPORTER="otlp",
    APCORE_TRACING_OTLP_ENDPOINT="http://localhost:4317",
    APCORE_METRICS_ENABLED=True,
    APCORE_LOGGING_ENABLED=True,
    APCORE_LOGGING_FORMAT="json",
)
```

When observability is enabled, the following middleware is automatically wired into the Executor:

| Middleware | Trigger | Purpose |
|---|---|---|
| TracingMiddleware | `TRACING_ENABLED` | Distributed tracing spans |
| MetricsMiddleware | `METRICS_ENABLED` | Latency histograms, call counts |
| ObsLoggingMiddleware | `LOGGING_ENABLED` | Structured log entries |
| ErrorHistoryMiddleware | Any of above | Ring buffer of recent errors |
| UsageMiddleware | `METRICS_ENABLED` | Per-module usage stats and trends |
| PlatformNotifyMiddleware | `SYS_MODULES_EVENTS_ENABLED` | Threshold-based event emission |

## System Modules

Enable built-in system modules for introspection and control:

```python
app.config.update(
    APCORE_SYS_MODULES_ENABLED=True,
    APCORE_SYS_MODULES_EVENTS_ENABLED=True,  # Optional: enable event system
)
```

This registers:
- `system.health.summary` / `system.health.module` — Health status
- `system.manifest.full` / `system.manifest.module` — Module introspection
- `system.usage.summary` / `system.usage.module` — Usage statistics
- `system.control.toggle_feature` / `system.control.update_config` / `system.control.reload_module` — Runtime control

## MCP Tool Explorer

The MCP Tool Explorer is a browser UI provided by [apcore-mcp](https://github.com/aipartnerup/apcore-mcp) for inspecting registered modules and executing them interactively.

> **Security:** Without JWT authentication, Explorer endpoints are unauthenticated. Either enable `--jwt-secret` or only expose in development/staging environments.

```bash
flask apcore serve --http --explorer --allow-execute \
    --explorer-title "My API Tools" \
    --explorer-project-name "My Project"
```

Browse to `http://127.0.0.1:9100/explorer/` to view the interactive explorer with Try-it execution.

## JWT Authentication

Protect MCP endpoints with JWT Bearer tokens (requires `apcore-mcp>=0.10.0`, HTTP transports only):

```bash
flask apcore serve --http \
    --jwt-secret "change-me-in-production" \
    --jwt-algorithm HS256 \
    --jwt-audience my-api \
    --jwt-issuer https://auth.example.com \
    --explorer --allow-execute
```

When JWT is enabled:
- All MCP endpoints require a valid `Authorization: Bearer <token>` header
- The Explorer UI shows a token input field for authentication
- Use `--no-require-auth` to allow unauthenticated access
- Use `--exempt-paths` to bypass auth for specific paths

## Approval System

Require approval for module execution (apcore-mcp 0.8.0+):

```bash
# Interactive approval via MCP elicitation
flask apcore serve --http --approval elicit

# Auto-approve all (testing)
flask apcore serve --http --approval auto-approve
```

## Docker Demo

A complete runnable demo is included in `examples/demo/`. It demonstrates the full pipeline: Flask CRUD routes with Pydantic schemas, route scanning, annotation inference, `@module` registration, MCP server, and observability.

```bash
cd examples/demo
docker compose up --build
```

See [examples/demo/README.md](examples/demo/README.md) for full details.

## Public API

```python
from flask_apcore import (
    Apcore,             # Flask Extension (unified entry point)
    module,             # @module decorator
    Registry,           # Module registry
    Executor,           # Module executor with middleware pipeline
    Context,            # Request context
    Identity,           # User identity
    ACL,                # Access control list
    Config,             # Executor configuration
    Middleware,          # Middleware base class
    ModuleAnnotations,  # Behavioral hints (readonly, destructive, etc.)
    ModuleDescriptor,   # Module metadata
    FunctionModule,     # Module wrapper for functions
    PreflightResult,    # Preflight validation result
    # Approval system
    ApprovalHandler,
    AutoApproveHandler,
    AlwaysDenyHandler,
    # Events
    EventEmitter,
    EventSubscriber,
    ApCoreEvent,
    # Cancellation
    CancelToken,
    # Errors
    ModuleError,
    ModuleNotFoundError,
    ACLDeniedError,
    SchemaValidationError,
    InvalidInputError,
    # System modules
    register_sys_modules,
)
```

## Development

```bash
git clone https://github.com/aipartnerup/flask-apcore.git
cd flask-apcore
pip install -e ".[dev,mcp]"
pytest
```

## License

Apache-2.0
