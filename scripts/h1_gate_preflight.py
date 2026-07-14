"""Solver-free validation entry point for the H1 licensed-gate inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evidence.h1_acceptance import (
    MAX_INPUT_BYTES,
    build_h1_dry_run_receipt,
    load_bounded_json,
    validate_h1_acceptance_contract,
)


DEFAULT_CONTRACT = ROOT / "release" / "integration_fixtures" / "h1_physical_evidence.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()

    contract = validate_h1_acceptance_contract(load_bounded_json(args.contract, MAX_INPUT_BYTES))
    spec = None
    if args.spec is not None:
        spec = load_bounded_json(args.spec, contract["limits"]["max_spec_bytes"])
    receipt = build_h1_dry_run_receipt(contract, spec, verify_files=args.verify_files)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
