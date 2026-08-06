"""The scoped-model mixin and the two introspection helpers built on it.

TalukaScopedMixin is the single marker every district-scoped table carries.
Phase 2's ORM read filter targets this mixin directly via
`with_loader_criteria(TalukaScopedMixin, ...)`, so every model that inherits
it — directly or through SchemeModelMixin — is enrolled in read isolation
automatically, with no per-model wiring.
"""
from typing import List, Type

from sqlalchemy import Column, String, UniqueConstraint
from sqlalchemy.ext.declarative import declared_attr

from src.core.taluka.constants import DISTRICT_LEVEL
from src.database import Base


class TalukaScopedMixin:
    """Marks a model as carrying the `taluka` row-role column.

    Must be declared with @declared_attr, not a plain class attribute:
    with_loader_criteria(TalukaScopedMixin, lambda cls: cls.taluka == ...)
    inspects the mixin's own class dict at criteria-registration time, and a
    plain attribute is not yet a mapped InstrumentedAttribute there.
    """

    @declared_attr
    def taluka(cls):
        return Column(
            String(100),
            nullable=False,
            default=DISTRICT_LEVEL,
            server_default=DISTRICT_LEVEL,
            index=True,
        )


def iter_scoped_models() -> List[Type]:
    """Every mapped class that carries TalukaScopedMixin."""
    return [
        mapper.class_
        for mapper in Base.registry.mappers
        if issubclass(mapper.class_, TalukaScopedMixin)
    ]


def natural_key_columns(model: Type) -> tuple:
    """The natural-key column names for `model`, excluding `taluka`.

    Every scoped table carries exactly one natural-key UniqueConstraint
    (verified against all 78 tables during design). Zero or more than one
    is a modeling error serious enough to fail loudly rather than fall back
    to a guess — a wrong natural key silently corrupts consolidation
    roll-ups and the write-redirection lookup in resolve_editable_row().
    """
    unique_constraints = [
        c for c in model.__table__.constraints if isinstance(c, UniqueConstraint)
    ]
    if len(unique_constraints) != 1:
        raise ValueError(
            f"{model.__name__} must declare exactly one UniqueConstraint to "
            f"serve as its natural key, found {len(unique_constraints)}"
        )
    return tuple(
        col.name for col in unique_constraints[0].columns if col.name != 'taluka'
    )
