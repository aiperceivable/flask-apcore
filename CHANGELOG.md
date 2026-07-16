# Changelog

All notable changes to this project will be documented in this file.

## [0.4.0] - 2026-07-15

Reachable role-based ACL governance for Flask routes + dependency uplift to the aligned apcore 0.26.0 / apcore-toolkit 0.10.0 / apcore-mcp 0.17.2 governance train. All tests pass.

### Added

- **ACL demo (`examples/acl_demo/`)** — runnable Flask app showing apcore Access Control List enforcement on module calls, matching the shared cross-integration contract: an `acl.yaml` (admins may call anything; `orders.list` public; else denied), routes that map `ACLDeniedError` → HTTP 403, and an `X-Roles` demo auth shortcut mapped to an apcore `Identity` via `FlaskContextFactory`. Covered end-to-end by `tests/test_acl_demo.py` (4 cases: admin allowed, anonymous/non-admin denied, public read).

### Fixed

- **`FlaskContextFactory` dropped roles** — it built `Identity(id=..., type="user")` without forwarding the user's roles, so apcore ACL rules keyed on `roles` (e.g. `roles: [admin]`) **never matched** and role-based access control silently did nothing from Flask routes. Roles are now propagated from `g.user.roles` / flask-login `current_user.roles` into `Identity(roles=...)`.
- **Package scanning aborted on Flask `g` / `request` members** — `_scan_packages_for_modules` called `hasattr(obj, "apcore_module")` on every module member; Flask's `g` / `request` are werkzeug `LocalProxy` objects that raise `RuntimeError` (not `AttributeError`) on attribute access outside an app context, so `hasattr` propagated and **aborted the scan mid-way**, silently dropping every `@module` function alphabetically after `g`. The scan now skips members that raise on attribute access.

### Changed

- **Dependency floors raised to the aligned governance train**: `apcore >= 0.26.0` (was `>= 0.14.0`; Execution Policy §7.9, governance events, no-handler fail-loud), `apcore-toolkit >= 0.10.0` (was `>= 0.2.0`), `apcore-mcp >= 0.17.2` (was `>= 0.10.0`; elicitation approval now sends a non-empty renderable schema).
- Trace-id test expectations updated for apcore 0.26's 32-char hex `trace_id` (previously a 36-char dash-separated UUID).

## [0.3.1] - 2026-03-22

### Changed
- Rebrand: aipartnerup → aiperceivable

## [0.3.0] - 2026-02-28

### Added
- JWT authentication for MCP endpoints: `--jwt-secret`, `--jwt-algorithm`, `--jwt-audience`, `--jwt-issuer` CLI flags and corresponding `APCORE_SERVE_JWT_SECRET`, `APCORE_SERVE_JWT_ALGORITHM`, `APCORE_SERVE_JWT_AUDIENCE`, `APCORE_SERVE_JWT_ISSUER` config settings (requires `apcore-mcp>=0.7.0`, HTTP transports only).
- Minimum secret length validation (16+ characters) for HMAC algorithms (HS256/HS384/HS512).

### Changed
- Bump `apcore-mcp` optional dependency from `>=0.6.0` to `>=0.7.0`.

## [0.2.1] - 2026-02-27

### Added
- Pydantic model flattening for registered modules in Apcore.
- Factory pattern example and new configuration options in README.

### Changed
- License changed to Apache-2.0.
- Refactored explorer functionality and settings.

## [0.2.0] - 2026-02-25

### Added
- MCP Serve Explorer passthrough: `--explorer`, `--explorer-prefix`, `--allow-execute` CLI flags and corresponding `APCORE_SERVE_EXPLORER`, `APCORE_SERVE_EXPLORER_PREFIX`, `APCORE_SERVE_ALLOW_EXECUTE` config settings, forwarded to `apcore_mcp.serve()`.

### Fixed
- Preserve `http_method` and `url_rule` in RegistryWriter metadata.
- Serialize Pydantic models correctly in call endpoint output.

### Changed
- Remove Flask Blueprint Explorer (`/apcore/` routes, `flask_apcore.web` module, `APCORE_EXPLORER_*` config settings) in favour of the apcore-mcp Tool Explorer available via `flask apcore serve --explorer`.
- Remove JSON / OpenAPI output writers (superseded by apcore-mcp explorer).
- Bump `apcore-mcp` optional dependency from `>=0.4.0` to `>=0.5.1`.

## [0.1.0] - 2026-02-23

### Added
- Initial release of `flask-apcore`.
- Flask extension for apcore AI-Perceivable Core integration.
- App-scoped Registry, Executor, and ContextFactory wrappers following Flask multi-app best practices.
- Direct registration of scanned modules into the apcore Registry via `RegistryWriter`.
- Support for user and observability middlewares, ACL, and executor config.
- Schema backends for Marshmallow, Pydantic, and type hints.
- Comprehensive test suite including async test support.
- Developer tooling: pytest, pytest-flask, pytest-asyncio, ruff, mypy, pre-commit, coverage.
