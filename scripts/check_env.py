#!/usr/bin/env python3
# Copyright (c) 2026 Ranil Fernando
# SPDX-License-Identifier: Apache-2.0
"""Pre-flight check: confirm dependencies, testbed and environment are usable.

Run this before wiring the server into VS Code so configuration problems surface
as readable text instead of an MCP start-up failure.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.config import Settings  # noqa: E402

REQUIRED_MODULES = ("mcp", "pyats", "genie", "unicon")
CREDENTIAL_VARS = ("CML_DEVICE_USERNAME", "CML_DEVICE_PASSWORD")


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="check_env.py",
        description="Validate the local environment for the Cisco pyATS MCP server.",
    )


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    problems: list[str] = []

    print(f"Python           : {sys.version.split()[0]} ({sys.executable})")

    for module in REQUIRED_MODULES:
        found = importlib.util.find_spec(module) is not None
        print(f"module {module:<10}: {'OK' if found else 'MISSING'}")
        if not found:
            problems.append(f"'{module}' is not installed. Run: pip install -r requirements.txt")

    settings = Settings.from_env()
    testbed = Path(settings.testbed_path).expanduser()
    print(f"testbed          : {testbed} ({'found' if testbed.is_file() else 'NOT FOUND'})")
    if not testbed.is_file():
        problems.append(
            "Testbed not found. Copy testbed/testbed.example.yaml to testbed/testbed.yaml "
            "and set PYATS_TESTBED to its absolute path."
        )

    for var in CREDENTIAL_VARS:
        print(f"{var:<17}: {'set' if os.environ.get(var) else 'NOT SET'}")
        if not os.environ.get(var):
            problems.append(f"{var} is not set; pyATS cannot resolve %ENV{{{var}}} in the testbed.")

    print(f"allow_config     : {settings.allow_config}")
    print(f"allow_save       : {settings.allow_save}")
    print(f"strict host keys : {settings.strict_host_key_checking}")

    if problems:
        print("\nProblems found:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print("\nEnvironment looks good.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
