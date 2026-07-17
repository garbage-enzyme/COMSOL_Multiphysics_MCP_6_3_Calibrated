"""Installed stdio probe result decoding tests."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from development_kit.scripts.installed_stdio_probe import _tool_payload


def test_tool_payload_accepts_structured_or_text_json_objects():
    assert _tool_payload(SimpleNamespace(structuredContent={"value": 1})) == {
        "value": 1
    }
    wrapped = SimpleNamespace(structuredContent={"result": {"value": 2}})
    assert _tool_payload(wrapped) == {"value": 2}
    text = SimpleNamespace(
        structuredContent=None,
        content=[SimpleNamespace(text=json.dumps({"value": 3}))],
    )
    assert _tool_payload(text) == {"value": 3}


def test_tool_payload_rejects_non_object_results():
    result = SimpleNamespace(
        structuredContent=None,
        content=[SimpleNamespace(text="[]")],
    )
    with pytest.raises(RuntimeError, match="JSON object"):
        _tool_payload(result)
