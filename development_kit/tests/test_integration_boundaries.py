"""Safety tests for standalone integration probe boundaries."""

from pathlib import Path
import runpy

import mph
import pytest


@pytest.mark.parametrize(
    "script_path",
    [
        "development_kit/tests/integration/probes/capacitor.py",
        "development_kit/tests/integration/probes/study_mesh.py",
        "development_kit/tests/integration/probes/unicode_save.py",
    ],
)
def test_loading_standalone_probe_does_not_create_client(monkeypatch, script_path):
    def fail_client_creation(*args, **kwargs):
        raise AssertionError("mph.Client must not be called while loading a probe")

    monkeypatch.setattr(mph, "Client", fail_client_creation)
    full_path = Path(__file__).parents[2] / script_path

    namespace = runpy.run_path(str(full_path), run_name="probe_import_test")

    assert callable(namespace["main"])
