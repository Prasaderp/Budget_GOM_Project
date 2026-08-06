"""The single ORM read-isolation interception point (docs/plan.md section 2.3).

A `do_orm_execute` listener bound to `SessionLocal` injects a
`with_loader_criteria(TalukaScopedMixin, ...)` predicate into every ORM
SELECT issued through the app's session factory — `query()`, 2.0-style
`select()`, subqueries, joins, column-only queries, all of it — with no
per-call-site change required. Callers that need every row (consolidation,
provisioning, the breakdown page) opt out explicitly via
`execution_options(taluka_scope_all=True)`.

The default, when no execution option is set, is always
`current_scope().taluka_value`, which defaults to the consolidated scope
(`''`) when no request context ever set one. A forgotten context therefore
degrades to today's behaviour, never to an unfiltered query and never to a
double count.

LANDMINE: `with_loader_criteria` does not apply to `Session.get()` /
`Query.get()` — those resolve against the identity map by primary key and
bypass SELECT-rendering entirely (documented SQLAlchemy behaviour, not a bug
here). Never use `.get()` on a TalukaScopedMixin model; use an explicit
`.filter(Model.id == id)` so this listener actually runs. Recipe R's
`resolve_editable_row()` (Phase 6) does this correctly by construction.
"""
from sqlalchemy import event
from sqlalchemy.orm import with_loader_criteria

from src.core.taluka.models import TalukaScopedMixin
from src.core.taluka.scope import current_scope
from src.database import SessionLocal

# Execution option a caller sets to bypass scoping entirely and see every
# row for a natural key (district office + all talukas + consolidated).
TALUKA_SCOPE_ALL_OPTION = "taluka_scope_all"


@event.listens_for(SessionLocal, "do_orm_execute")
def _inject_taluka_scope_filter(execute_state):
    if not execute_state.is_select:
        return
    if execute_state.execution_options.get(TALUKA_SCOPE_ALL_OPTION, False):
        return

    # Read the scope value once per execution, outside the lambda body, so
    # it is captured as a closure variable. SQLAlchemy's lambda-SQL layer
    # tracks closure variables and turns them into bound parameters that are
    # re-read on every invocation instead of being baked into a cached plan
    # — this is what makes two different scopes in the same process return
    # different rows rather than sharing a stale compiled query.
    scope_value = current_scope().taluka_value

    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TalukaScopedMixin,
            lambda cls: cls.taluka == scope_value,
            include_aliases=True,
        )
    )
