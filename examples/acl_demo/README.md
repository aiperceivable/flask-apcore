# flask-apcore ACL demo

Shows how a Flask application enforces apcore **Access Control Lists (ACL)** on
apcore module calls made from within request handlers — the same `orders.delete`
(admins only) / `orders.list` (public read) contract used across the apcore
framework integrations.

## What it shows

| Call | Roles | Result |
| --- | --- | --- |
| `DELETE /orders/1` | *(none — anonymous)* | **403** |
| `DELETE /orders/1` | `user` | **403** |
| `DELETE /orders/1` | `admin` | **200** `{"deleted": 1}` |
| `GET /orders` | *(any)* | **200** (read is public) |

## How it works

1. `APCORE_ACL_PATH` points apcore at [`acl.yaml`](./acl.yaml). flask-apcore's
   Executor loads it (`ACL.load(path)`) and enforces it on every module call.
2. A (simulated) `before_request` hook reads a comma-separated `X-Roles` header
   and attaches a user with `roles` to `g.user`.
3. Each route builds an apcore `Context` from the request via
   `FlaskContextFactory` (which turns `g.user` into an `Identity(roles=...)`) and
   calls a module with `apcore.call(module_id, ..., context=ctx)`.
4. The Executor checks the ACL before running the module. A denied call raises
   `ACLDeniedError`, which the route maps to HTTP 403.

`acl.yaml` (first-match-wins, `default_effect: deny`):

- **admins** (`roles: [admin]`) may call any module;
- **anyone** (including anonymous) may call `orders.list`;
- everything else falls through to `deny`.

## Run it

```bash
export APCORE_ACL_PATH=examples/acl_demo/acl.yaml   # optional; app sets a default
flask --app examples.acl_demo.app run

curl -X DELETE localhost:5000/orders/1                       # 403 (anonymous)
curl -X DELETE localhost:5000/orders/1 -H 'X-Roles: user'    # 403 (not admin)
curl -X DELETE localhost:5000/orders/1 -H 'X-Roles: admin'   # 200
curl localhost:5000/orders                                   # 200 (read is public)
```

> **NOTE:** The `X-Roles` header is a demo shortcut standing in for real
> authentication. In production, resolve the user from a JWT/session
> `before_request` and set `g.user` there instead.
