"""Flask + apcore ACL demo.

Shows how a Flask application enforces apcore Access Control Lists (ACL) on
apcore module calls made from within request handlers.

How it works
------------
1. ``APCORE_ACL_PATH`` points apcore at ``acl.yaml``. flask-apcore's Executor
   loads it (``ACL.load(path)``) and enforces it on every module call.
2. A (simulated) ``before_request`` hook attaches a user with ``roles`` to
   ``g.user``.
3. Each route builds an apcore ``Context`` from the request via
   ``FlaskContextFactory`` (which turns ``g.user`` into an ``Identity(roles=...)``)
   and calls a module with ``apcore.call(module_id, ..., context=ctx)``.
4. The Executor checks the ACL before running the module. A denied call raises
   ``ACLDeniedError``, which the route maps to HTTP 403.

Run it::

    export APCORE_ACL_PATH=examples/acl_demo/acl.yaml   # optional; app sets a default
    flask --app examples.acl_demo.app run

Then::

    curl -X DELETE localhost:5000/orders/1                       # 403 (anonymous)
    curl -X DELETE localhost:5000/orders/1 -H 'X-Roles: user'    # 403 (not admin)
    curl -X DELETE localhost:5000/orders/1 -H 'X-Roles: admin'   # 200
    curl localhost:5000/orders                                   # 200 (read is public)

NOTE: The ``X-Roles`` header is a demo shortcut standing in for real
authentication. In production, resolve the user from a JWT/session
``before_request`` and set ``g.user`` there instead.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, g, jsonify, request

from flask_apcore import ACLDeniedError, Apcore, module
from flask_apcore.registry import get_context_factory

# Point apcore at this demo's ACL file unless the caller already set one.
os.environ.setdefault("APCORE_ACL_PATH", str(Path(__file__).parent / "acl.yaml"))


# Two apcore modules protected by acl.yaml:
#   orders.delete -> admins only
#   orders.list   -> public (read)
@module(id="orders.delete")
def delete_order(order_id: int) -> dict:
    return {"deleted": order_id}


@module(id="orders.list")
def list_orders() -> dict:
    return {"orders": [{"id": 1}, {"id": 2}]}


def _fake_auth() -> None:
    """Stand-in for real authentication.

    Reads a comma-separated ``X-Roles`` header and attaches a user object to
    ``g.user``. Real apps should do this from a JWT/session ``before_request``;
    the shape (``id`` + ``roles``) is what FlaskContextFactory reads.
    """
    x_roles = request.headers.get("X-Roles")
    if x_roles:
        g.user = SimpleNamespace(
            id="u1",
            roles=[r.strip() for r in x_roles.split(",") if r.strip()],
            is_authenticated=True,
        )
    # No header -> no g.user -> FlaskContextFactory yields an anonymous Identity.


def create_demo_app() -> Flask:
    """Build the demo Flask app with two ACL-protected apcore modules."""
    app = Flask(__name__)
    app.config.update(
        APCORE_ACL_PATH=os.environ["APCORE_ACL_PATH"],
        APCORE_AUTO_DISCOVER=True,
        # Scan this module for the @module-decorated order functions.
        APCORE_MODULE_PACKAGES=[__name__],
    )
    apcore = Apcore(app)

    app.before_request(_fake_auth)

    def _call(module_id: str, inputs: dict):
        # Build the apcore Context from the current request so the Identity
        # (and its roles) reach the Executor's ACL check.
        ctx = get_context_factory().create_context(request=request)
        return apcore.call(module_id, inputs, context=ctx)

    @app.delete("/orders/<int:order_id>")
    def delete_order_route(order_id: int):
        try:
            return jsonify(_call("orders.delete", {"order_id": order_id}))
        except ACLDeniedError as exc:
            return jsonify({"detail": str(exc)}), 403

    @app.get("/orders")
    def list_orders_route():
        try:
            return jsonify(_call("orders.list", {}))
        except ACLDeniedError as exc:
            return jsonify({"detail": str(exc)}), 403

    return app


app = create_demo_app()
