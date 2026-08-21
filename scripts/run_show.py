#!/usr/bin/env python3

# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0
"""Verify pyATS can reach a device, independently of MCP or VS Code.

Run this first when troubleshooting: if it fails, the problem is connectivity or
credentials, not the MCP server.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.config import Settings  # noqa: E402
from mcp_server.devices import connected_device  # noqa: E402
from mcp_server.validation import validate_show_command  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_show.py",
        description="Run a read-only show command against a testbed device using pyATS.",
        epilog="Example: python scripts/run_show.py --device iosv-0 "
        '--command "show ip interface brief"',
    )
    parser.add_argument(
        "-d",
        "--device",
        required=True,
        help="Device name as defined in the pyATS testbed (for example: iosv-0).",
    )
    parser.add_argument(
        "-c",
        "--command",
        default="show ip interface brief",
        help="Show command to execute. Default: %(default)s",
    )
    parser.add_argument(
        "-t",
        "--testbed",
        help="Path to the testbed YAML file. Overrides the PYATS_TESTBED variable.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argv is None and len(sys.argv) == 1:
        parser.print_help()
        return 1

    args = parser.parse_args(argv)
    if args.testbed:
        os.environ["PYATS_TESTBED"] = args.testbed

    try:
        settings = Settings.from_env()
        command = validate_show_command(args.command)
        with connected_device(settings, args.device) as device:
            print(device.execute(command, timeout=settings.command_timeout))
    except Exception as exc:  # noqa: BLE001 - user-facing CLI, print a clean message
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
