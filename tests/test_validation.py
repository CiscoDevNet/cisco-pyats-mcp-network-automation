# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for the command guardrails. These run without pyATS or a live device."""

from __future__ import annotations

import pytest

from mcp_server.validation import (
    CommandNotAllowedError,
    truncate,
    validate_config,
    validate_show_command,
)


@pytest.mark.parametrize(
    "command",
    [
        "show version",
        "  show ip interface brief  ",
        "show running-config | section interface",
        "show processes cpu | include one minute",
        "show ip route | count Gi",
    ],
)
def test_accepts_read_only_commands(command: str) -> None:
    assert validate_show_command(command) == command.strip()


@pytest.mark.parametrize(
    "command",
    [
        "",
        "   ",
        "configure terminal",
        "reload",
        "show version; reload",
        "show version && reload",
        "show version\nreload",
        "show running-config | redirect flash:cfg.txt",
        "show running-config | tee flash:cfg.txt",
        "show run | include a | include b",
        "show run |",
        "show version `id`",
        "show version $(id)",
        "show version > flash:out.txt",
        "show " + "a" * 600,
    ],
)
def test_rejects_unsafe_show_commands(command: str) -> None:
    with pytest.raises(CommandNotAllowedError):
        validate_show_command(command)


def test_accepts_benign_config() -> None:
    config = """
    interface loopback123
     description created-by-mcp
     ip address 10.123.123.1 255.255.255.255
    """
    assert validate_config(config) == [
        "    interface loopback123",
        "     description created-by-mcp",
        "     ip address 10.123.123.1 255.255.255.255",
    ]


@pytest.mark.parametrize(
    "config",
    [
        "",
        "reload",
        "write erase",
        "erase startup-config",
        "delete flash:image.bin",
        "format flash:",
        "username hacker privilege 15 secret Passw0rd",
        "no username admin",
        "enable secret Passw0rd",
        "no aaa new-model",
        "no ip ssh version 2",
        "crypto key zeroize rsa",
        "boot system flash:other.bin",
        "config-register 0x2142",
        "interface loopback1\nreload",
    ],
)
def test_rejects_destructive_config(config: str) -> None:
    with pytest.raises(CommandNotAllowedError):
        validate_config(config)


def test_rejects_oversized_config() -> None:
    with pytest.raises(CommandNotAllowedError):
        validate_config("\n".join(f"description line {i}" for i in range(500)))


def test_truncate_clamps_long_output() -> None:
    assert truncate("abc", 10) == "abc"
    clamped = truncate("x" * 100, 10)
    assert clamped.startswith("x" * 10)
    assert "truncated" in clamped
