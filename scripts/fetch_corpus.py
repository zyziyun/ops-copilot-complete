"""Write the four-source ops corpus to data/ as markdown with front-matter.

Each of the four sources is permissively licensed (see README "Corpus sources
and licenses"). Rather than scrape live docs at class time — which is fragile
and rate-limited — we ship a fixed, curated set of excerpts from each source so
the pipeline is fully reproducible offline. Each file carries a
``source_system`` front-matter tag that ingestion records on every chunk, which
is what C2's filtering and attribution build on.

The four sources, chosen for two retrieval-difficulty scenarios:
  - gitlab   : GitLab Runbooks (MIT)              — operating context
  - postgres : PostgreSQL docs (PostgreSQL Lic.)  — the system being operated
  - fastapi  : FastAPI docs (MIT)                 — near-domain (near-neighbor)
  - django   : Django docs (BSD 3-Clause)         — far-domain (cross leakage)
"""
from pathlib import Path

DATA = Path("data")

CORPUS: dict[str, str] = {
    "gitlab": """---
source_system: gitlab
title: GitLab Runbooks — Postgres on-call excerpts
license: MIT
url: https://gitlab.com/gitlab-com/runbooks
---

# Postgres replication lag

When a replica falls behind the primary, first check replication lag with
`SELECT now() - pg_last_xact_replay_timestamp();` on the replica. Sustained lag
usually means the replica cannot keep up with WAL volume: look for long-running
queries holding snapshots, a saturated disk on the replica, or a network
bottleneck between primary and replica. To troubleshoot Postgres replication
lag, confirm the WAL sender and receiver processes are alive, check
`pg_stat_replication` on the primary, and watch `pg_stat_wal_receiver` on the
replica. If lag keeps growing, consider pausing heavy reporting queries on the
replica or temporarily raising `wal_keep_size` on the primary.

# Database got slow after a deploy

If the database got slow right after a deploy, start with what changed. Check
for new or altered queries shipped in the release, missing indexes on new
columns, and a spike in connections from the new code path. Run the slow-query
inspection: look at `pg_stat_activity` for active statements older than a few
seconds, and `pg_stat_statements` for the queries whose total time jumped after
the deploy. A common cause is a new N+1 query pattern or an ORM change that
dropped an index hint. Roll back the deploy if a single query is saturating the
database while you craft an index fix.

# Connection saturation alert (connections near max)

When connections approach `max_connections`, the runbook is: inspect current
usage with `SELECT count(*) FROM pg_stat_activity;`, identify idle-in-
transaction sessions and stuck backends, and terminate the worst offender with
`pg_terminate_backend(pid)` only after confirming it is safe. File an incident
ticket capturing the pid, the query, and the action taken. The durable fix is a
connection pooler (PgBouncer) and right-sizing application pool_size, not raising
max_connections indefinitely.
""",
    "postgres": """---
source_system: postgres
title: PostgreSQL documentation — error and troubleshooting excerpts
license: PostgreSQL License
url: https://www.postgresql.org/docs/
---

# FATAL: could not create any TCP/IP sockets

The server error `FATAL: could not create any TCP/IP sockets` means the
postmaster could not bind any of the requested listen addresses and ports.
Common causes: another postgres instance is already listening on the same port,
the configured `listen_addresses` references an address not present on the host,
or the port is in use by another process. Check with `ss -ltnp | grep 5432`,
fix `listen_addresses`/`port` in `postgresql.conf`, and restart.

# Configuring pg_hba.conf authentication

Client authentication is controlled by the `pg_hba.conf` file. Each record
specifies a connection type, a client address range, a database name, a user
name, and the authentication method (for example `scram-sha-256`, `md5`,
`trust`, or `peer`). To configure pg_hba.conf authentication, add a line such as
`host  all  all  10.0.0.0/8  scram-sha-256`, then reload with
`SELECT pg_reload_conf();`. Order matters: the first matching record is used. A
wrong or missing entry produces `no pg_hba.conf entry for host ...`.

# Too many connections and max_connections

The server-side ceiling on concurrent connections is `max_connections` (default
100). When clients exceed it Postgres rejects new connections with
`FATAL: sorry, too many connections`. Under load you tune this on the server
side by raising `max_connections` (within RAM limits, each connection costs
memory) or, far better, by putting a connection pooler in front so the database
sees a bounded number of backends. The application-side pool is a different
knob from `max_connections`.

# Migration failed: relation does not exist

A failed schema migration that reports `relation "x" does not exist` usually
means migrations were applied out of order, or the migration ran against the
wrong database. To check a failed migration: confirm the migration history table
matches what is deployed, verify you are connected to the intended database, and
re-run `alembic upgrade head` (or the equivalent) against the correct target.
Never edit applied migrations in place; add a new one.
""",
    "fastapi": """---
source_system: fastapi
title: FastAPI documentation — async and database excerpts
license: MIT
url: https://github.com/fastapi/fastapi
---

# Configuring the database connection pool

When using SQLAlchemy with an async engine, the application-side connection pool
is configured on `create_async_engine`. The key knobs are `pool_size` (the
number of persistent connections kept open) and `max_overflow` (extra
connections opened temporarily under burst). Together they cap how many
connections a single worker holds. Set `pool_pre_ping=True` to detect stale
connections. How you should configure the connection pool depends on how many
workers you run: the per-worker pool multiplies by the worker count, so size it
against the database's own connection limit.

# Too many connections under load

If the application raises connection-pool timeouts or the database reports too
many connections under load, the application-side fix is to bound `pool_size`
and `max_overflow` and ensure sessions are always returned to the pool (use the
dependency that closes the session per request). Opening a new connection per
request instead of using the pool is the classic cause of connection exhaustion
in async services.

# Async endpoints and the event loop

Define an endpoint with `async def` when it awaits I/O such as a database query
or an HTTP call, so the event loop can serve other requests while it waits. Use
a plain `def` endpoint for CPU-bound or sync-only work; FastAPI runs those in a
thread pool. Never call a blocking function inside `async def`, or you freeze the
loop for every concurrent request.
""",
    "django": """---
source_system: django
title: Django documentation — troubleshooting and FAQ excerpts
license: BSD 3-Clause
url: https://github.com/django/django
---

# NoReverseMatch in Django

`NoReverseMatch` is raised by Django's URL reverser when no URL pattern matches
the name and arguments you passed to `reverse()` or the `{% url %}` template tag.
Why am I getting NoReverseMatch in Django: the usual causes are a typo in the URL
pattern `name`, a missing or mismatched positional/keyword argument, an app
namespace you forgot to include (`myapp:detail` vs `detail`), or a pattern whose
regex/path converter does not accept the value you gave. Fix it by matching the
view name and the exact arguments the pattern expects.

# Django schema migrations

Django manages schema changes with its own migrations framework. `makemigrations`
generates migration files from model changes and `migrate` applies them. If a
migration conflict appears, Django asks you to merge migrations. This is the
application framework's migration system and is unrelated to operating a
PostgreSQL server; a Django migration failure is a code/model issue, not a
database server incident.

# Common Django FAQ

Static files not loading in production usually means `collectstatic` was not run
or the web server is not configured to serve `STATIC_ROOT`. A `TemplateDoesNotExist`
error means the template loader cannot find the file on any configured template
directory. These are web-framework troubleshooting items with little overlap with
database operations.
""",
}


def main() -> None:
    DATA.mkdir(exist_ok=True)
    for system, body in CORPUS.items():
        path = DATA / f"{system}.md"
        path.write_text(body, encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
