"""Write the ops corpus to data/ as markdown with structured front-matter.

Two modes:
  python scripts/fetch_corpus.py          # bundled, curated, offline-reproducible
  python scripts/fetch_corpus.py --live   # ALSO pull real pages from GitHub raw

The bundled set is the deterministic base the golden eval targets. ``--live``
augments it with real upstream docs (FastAPI, Django) for volume. Front-matter
carries ``source_system`` plus structured fields (doc_type, severity, …) that
become each chunk's queryable ``doc_metadata``.
"""
import sys
from pathlib import Path

import httpx

DATA = Path("data")

CORPUS: dict[str, str] = {
    "gitlab": """---
source_system: gitlab
doc_type: runbook
license: MIT
url: https://gitlab.com/gitlab-com/runbooks
---

# Postgres replication lag

When a replica falls behind the primary, first check replication lag with
`SELECT now() - pg_last_xact_replay_timestamp();` on the replica. Sustained lag
usually means the replica cannot keep up with WAL volume: look for long-running
queries holding snapshots, a saturated disk on the replica, or a network
bottleneck. To troubleshoot Postgres replication lag, confirm the WAL sender and
receiver processes are alive, check `pg_stat_replication` on the primary, and
watch `pg_stat_wal_receiver` on the replica. If lag keeps growing, pause heavy
reporting queries on the replica or temporarily raise `wal_keep_size`.

# Database got slow after a deploy

If the database got slow right after a deploy, start with what changed. Check for
new or altered queries shipped in the release, missing indexes on new columns,
and a spike in connections. Look at `pg_stat_activity` for active statements
older than a few seconds, and `pg_stat_statements` for queries whose total time
jumped. A common cause is a new N+1 pattern or an ORM change that dropped an
index. Roll back the deploy if a single query is saturating the database.

# Connection saturation alert (connections near max)

When connections approach `max_connections`, inspect usage with
`SELECT count(*) FROM pg_stat_activity;`, identify idle-in-transaction sessions
and stuck backends, and terminate the worst offender with
`pg_terminate_backend(pid)` only after confirming it is safe. File an incident
ticket capturing the pid, the query, and the action taken. The durable fix is a
connection pooler (PgBouncer) and right-sizing application pool_size.

# Disk filling up on the database host

A database host running out of disk is a high-severity incident. The usual
culprits are unrotated WAL, a runaway temp file from a huge sort, or bloat. Check
`df -h`, then `SELECT pg_size_pretty(pg_database_size('app'));` and the size of
`pg_wal`. If WAL is the problem, confirm archiving is keeping up and that no
replication slot is stuck holding WAL. Never delete files in `pg_wal` by hand.

# Severity reference table

| signal | severity | first action |
|---|---|---|
| connections > 90% of max | high | find and terminate stuck backends |
| replication lag > 5 min | high | check WAL volume and replica disk |
| disk > 85% on db host | critical | free WAL / temp, page the DBA |
| slow query after deploy | medium | inspect pg_stat_statements, consider rollback |
""",
    "postgres": """---
source_system: postgres
doc_type: reference
license: PostgreSQL License
url: https://www.postgresql.org/docs/
---

# FATAL: could not create any TCP/IP sockets

The server error `FATAL: could not create any TCP/IP sockets` means the
postmaster could not bind any requested listen address and port. Common causes:
another postgres instance already listens on the port, `listen_addresses`
references an address not on the host, or the port is in use. Check with
`ss -ltnp | grep 5432`, fix `listen_addresses`/`port` in `postgresql.conf`,
restart.

# Configuring pg_hba.conf authentication

Client authentication is controlled by `pg_hba.conf`. Each record gives a
connection type, client address range, database, user, and method (for example
`scram-sha-256`, `md5`, `trust`, `peer`). To configure pg_hba.conf
authentication, add a line like `host all all 10.0.0.0/8 scram-sha-256`, then
reload with `SELECT pg_reload_conf();`. The first matching record wins. A wrong
or missing entry produces `no pg_hba.conf entry for host ...`.

# Too many connections and max_connections

The server-side ceiling is `max_connections` (default 100). When clients exceed
it Postgres rejects new connections with `FATAL: sorry, too many connections`.
Raise `max_connections` within RAM limits (each connection costs memory) or, far
better, put a connection pooler in front so the database sees a bounded number of
backends. The application-side pool is a different knob from `max_connections`.

# Migration failed: relation does not exist

A failed migration reporting `relation "x" does not exist` usually means
migrations applied out of order, or against the wrong database. Confirm the
migration history table matches what is deployed, verify the target database, and
re-run `alembic upgrade head` against the correct target. Never edit applied
migrations in place; add a new one.

# Deadlock detected

`ERROR: deadlock detected` means two transactions each hold a lock the other
needs. Postgres aborts one to break the cycle. Fix it by making transactions
acquire locks in a consistent order, keeping them short, and reviewing
`pg_locks`. Retrying the aborted transaction is normal.

# Autovacuum and bloat

Dead tuples from updates and deletes accumulate as bloat until autovacuum
reclaims them. If a table bloats, check `pg_stat_user_tables.n_dead_tup` and
whether autovacuum is keeping up; a long-running transaction can hold back the
xmin horizon and block cleanup. Tune `autovacuum_vacuum_scale_factor` for large
hot tables.
""",
    "fastapi": """---
source_system: fastapi
doc_type: framework
license: MIT
url: https://github.com/fastapi/fastapi
---

# Configuring the database connection pool

With an async SQLAlchemy engine the application-side pool is configured on
`create_async_engine`. The key knobs are `pool_size` (persistent connections
kept open) and `max_overflow` (extra connections under burst); together they cap
how many connections one worker holds. Set `pool_pre_ping=True` to detect stale
connections. How you configure the connection pool depends on worker count: the
per-worker pool multiplies by workers, so size it against the database's own
limit.

# Too many connections under load

If the app raises pool timeouts or the database reports too many connections,
bound `pool_size` and `max_overflow` and ensure sessions are always returned to
the pool (use the per-request dependency that closes the session). Opening a new
connection per request instead of using the pool is the classic cause of
exhaustion.

# Async endpoints and the event loop

Define an endpoint with `async def` when it awaits I/O (a DB query or HTTP call)
so the event loop serves other requests while it waits. Use plain `def` for
CPU-bound or sync-only work; FastAPI runs those in a thread pool. Never call a
blocking function inside `async def`, or you freeze the loop for every request.

# Dependencies and lifespan

FastAPI dependencies inject per-request resources (a DB session) and guarantee
cleanup. The `lifespan` context manager runs startup/shutdown once per process;
use it to verify the database is reachable before serving and to dispose the pool
on shutdown.
""",
    "django": """---
source_system: django
doc_type: framework
license: BSD 3-Clause
url: https://github.com/django/django
---

# NoReverseMatch in Django

`NoReverseMatch` is raised by Django's URL reverser when no pattern matches the
name and arguments passed to `reverse()` or `{% url %}`. Why am I getting
NoReverseMatch in Django: usual causes are a typo in the pattern `name`, a missing
or mismatched argument, an app namespace you forgot (`myapp:detail` vs `detail`),
or a converter that rejects the value. Fix it by matching the view name and the
exact arguments the pattern expects.

# Django schema migrations

Django manages schema changes with its own migrations. `makemigrations`
generates files from model changes; `migrate` applies them. On a conflict Django
asks you to merge migrations. This is the framework's migration system and is
unrelated to operating a PostgreSQL server; a Django migration failure is a
code/model issue, not a database incident.

# Common Django FAQ

Static files not loading in production usually means `collectstatic` was not run
or the server is not serving `STATIC_ROOT`. A `TemplateDoesNotExist` error means
the loader cannot find the template on any configured directory. These are
web-framework troubleshooting items with little overlap with database operations.
""",
}

# (url, source_system, filename) — real upstream docs, fetched only with --live
LIVE_SOURCES = [
    (
        "https://raw.githubusercontent.com/fastapi/fastapi/master/docs/en/docs/async.md",
        "fastapi",
        "fastapi_async_live.md",
    ),
    (
        "https://raw.githubusercontent.com/django/django/main/docs/faq/general.txt",
        "django",
        "django_faq_live.md",
    ),
]


def write_bundled() -> None:
    for system, body in CORPUS.items():
        path = DATA / f"{system}.md"
        path.write_text(body, encoding="utf-8")
        print(f"wrote {path}")


def fetch_live() -> None:
    for url, system, fname in LIVE_SOURCES:
        try:
            r = httpx.get(url, timeout=15, follow_redirects=True)
            r.raise_for_status()
            body = f"---\nsource_system: {system}\ndoc_type: upstream\nurl: {url}\n---\n\n{r.text}"
            (DATA / fname).write_text(body, encoding="utf-8")
            print(f"fetched {fname} ({len(r.text)} chars)")
        except Exception as e:  # network is best-effort; bundled is the base
            print(f"skip {url}: {e}")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    write_bundled()
    if "--live" in sys.argv:
        fetch_live()


if __name__ == "__main__":
    main()
