"""Scene rigs (camera orbit, camera fit, light rig) live in the add-on, extension/easy_text/rigs.py, so one copy
serves both the demo build and the add-on. This module loads that file by path for the build scripts."""

from __future__ import annotations

import importlib.util
import pathlib
import sys

_PATH = pathlib.Path(__file__).resolve().parents[2] / "extension" / "easy_text" / "rigs.py"
_spec = importlib.util.spec_from_file_location("easy_text_rigs", _PATH)
_module = importlib.util.module_from_spec(_spec)
sys.modules["easy_text_rigs"] = _module
_spec.loader.exec_module(_module)
globals().update({name: getattr(_module, name) for name in _module.__all__})
__all__ = _module.__all__
