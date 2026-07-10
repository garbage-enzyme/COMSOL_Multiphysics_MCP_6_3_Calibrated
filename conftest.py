"""Pytest collection guard for legacy COMSOL probe scripts.

Root-level ``test_*.py`` files are manual integration probes that create real
COMSOL clients at import time. Unit tests live under ``tests/``.
"""

from pathlib import Path


collect_ignore = [
    str(path)
    for path in Path(__file__).parent.glob("test_*.py")
]
