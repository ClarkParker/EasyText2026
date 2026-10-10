"""Asset catalog (blender_assets.cats.txt). The UUIDs are fixed so catalogs stay stable."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Catalog:
    path: str
    uuid: str

    @property
    def simple_name(self) -> str:
        return self.path.replace("/", "-")


ROOT = Catalog("Easy Text", "7ed3049d-2082-4f93-a0fe-900274de8933")
TEXT = Catalog("Easy Text/Text", "74b5e1ad-b2e0-48e7-91c1-90eab3202d7c")
MESH = Catalog("Easy Text/Mesh", "6d57f253-3f12-4b6d-a31d-00e18e002356")
SELECTORS = Catalog("Easy Text/Selectors", "147e10f1-7540-4192-b86c-f60e22bf186d")
ANIMATORS = Catalog("Easy Text/Animators", "646e5d61-d88e-415c-a574-b8742b7cd394")
SCENE = Catalog("Easy Text/Scene", "780b7588-35f0-4fd5-880b-4f8e140bc779")
UTILS = Catalog("Easy Text/Utilities", "ec6ff2df-0a93-4c70-8fe4-0f200bca0b9f")

ALL = [ROOT, TEXT, MESH, SELECTORS, ANIMATORS, SCENE, UTILS]

HEADER = """# This is an Asset Catalog Definition file for Blender.
#
# Empty lines and lines starting with `#` will be ignored.
# The first non-ignored line should be the version indicator.
# Other lines are of the format "UUID:catalog/path/for/assets:simple catalog name"

VERSION 1
"""


def render() -> str:
    lines = [HEADER]
    for cat in ALL:
        lines.append(f"{cat.uuid}:{cat.path}:{cat.simple_name}")
    return "\n".join(lines) + "\n"


def write(path: Path) -> None:
    path.write_text(render(), encoding="utf-8")
