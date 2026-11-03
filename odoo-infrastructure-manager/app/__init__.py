"""Compatibility namespace for the infrastructure engine.

Runtime implementation lives in :mod:`infrastructure_engine`; legacy ``app.*``
imports remain supported for existing scripts and integrations.
"""
from pathlib import Path
from types import ModuleType
import sys

for _name in ("models", "services", "workflows", "ui", "validators", "core"):
    _module_name = f"app.{_name}"
    if _module_name not in sys.modules:
        _module = ModuleType(_module_name)
        _module.__path__ = [str(Path(__file__).resolve().parent.parent / "infrastructure_engine" / _name)]
        _module.__package__ = _module_name
        sys.modules[_module_name] = _module
