"""Reihenfolge der Gruppen-Builder. Abhängigkeiten (Untergruppen) stehen vor ihren Nutzern."""

from . import et_smoke

MODULES = [et_smoke]


def names() -> list[str]:
    return [m.NAME for m in MODULES]


def build_all() -> list:
    return [m.build() for m in MODULES]
