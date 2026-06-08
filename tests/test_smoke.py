"""Import-smoke test for TruthCert_v3.1.0_modeling (Bucket-B no-tests remediation).

Guards against dependency drift / syntax breakage in the main module.
"""
import importlib.util
import os
import sys

import pytest

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '04_reference_workflow.py')


def _load():
    sys.path.insert(0, os.path.dirname(_SCRIPT))
    spec = importlib.util.spec_from_file_location("smoke_mod", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    saved_out, saved_err = sys.stdout, sys.stderr
    if not hasattr(sys.stdout, "buffer"):
        sys.stdout = sys.__stdout__
    if not hasattr(sys.stderr, "buffer"):
        sys.stderr = sys.__stderr__
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    return mod


def test_script_exists():
    assert os.path.isfile(_SCRIPT), _SCRIPT


def test_module_imports():
    assert _load() is not None


def test_has_public_callable():
    mod = _load()
    publics = [n for n in dir(mod) if callable(getattr(mod, n)) and not n.startswith("_")]
    assert publics, "module exposes no public callable"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
