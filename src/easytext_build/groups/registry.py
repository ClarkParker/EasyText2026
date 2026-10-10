"""Order of the group builders. Dependencies (sub-groups) come before their users."""

from . import et_bevel, et_finish, et_lines_join, et_outline, et_solid, et_text_mesh, et_text_source, et_uv

MODULES = [et_lines_join, et_text_source, et_outline, et_solid, et_bevel, et_uv, et_finish, et_text_mesh]
MAIN = et_text_mesh.NAME


def names() -> list[str]:
    return [m.NAME for m in MODULES]


def build_all() -> list:
    return [m.build() for m in MODULES]
