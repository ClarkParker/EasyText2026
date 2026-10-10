"""Reihenfolge der Gruppen-Builder. Abhängigkeiten (Untergruppen) stehen vor ihren Nutzern."""

from . import et_lines_join, et_text_mesh

MODULES = [et_lines_join, et_text_mesh]
MAIN = et_text_mesh.NAME


def names() -> list[str]:
    return [m.NAME for m in MODULES]


def build_all() -> list:
    return [m.build() for m in MODULES]
