"""Model-scoped hooks for derived data maintained inside write transactions."""

from collections.abc import Callable
from typing import Any


DerivationHook = Callable[..., Any]
_HOOKS: dict[type, DerivationHook] = {}


def register(model: type, hook: DerivationHook) -> None:
    """Register one derivation hook for a mapped model.

    Re-importing the same module is harmless; replacing an existing model's
    hook with different behavior is rejected because import order must not
    decide which business rule runs.
    """
    existing = _HOOKS.get(model)
    if existing is not None and existing is not hook:
        raise RuntimeError(f"Derivation hook already registered for {model.__name__}")
    _HOOKS[model] = hook


def is_registered(model: type) -> bool:
    """Return whether mutations for ``model`` have a derivation hook."""
    return model in _HOOKS


def run_for(db, model: type, row, request, **context):
    """Run the model's hook, or return ``None`` when it has none."""
    hook = _HOOKS.get(model)
    return hook(db, row, request, **context) if hook is not None else None
