# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0
"""Guardrails applied to every command an LLM asks the server to run.

The MCP client is driven by a language model, so any string reaching a device is
treated as untrusted input. These helpers enforce an allow-list for read-only
commands and a deny-list for service-impacting configuration.
"""

from __future__ import annotations

import re

MAX_COMMAND_LENGTH = 512
MAX_CONFIG_LINES = 200

# IOS pipe modifiers that only filter output. `redirect`, `tee` and `append`
# write files on the device and are deliberately excluded.
ALLOWED_PIPE_MODIFIERS = frozenset({"begin", "count", "exclude", "include", "section"})

# Characters that would let a caller smuggle a second command into one string.
_COMMAND_SEPARATORS = re.compile(r"[;&\r\n`$<>]")

_DESTRUCTIVE_CONFIG_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^\s*(no\s+)?boot\s+system\b", re.I), "changing the boot image"),
    (re.compile(r"^\s*erase\b", re.I), "erasing storage"),
    (re.compile(r"^\s*write\s+erase\b", re.I), "erasing the startup configuration"),
    (re.compile(r"^\s*format\b", re.I), "formatting storage"),
    (re.compile(r"^\s*delete\b", re.I), "deleting files"),
    (re.compile(r"^\s*reload\b", re.I), "reloading the device"),
    (re.compile(r"^\s*(no\s+)?username\b", re.I), "managing local user accounts"),
    (re.compile(r"^\s*(no\s+)?enable\s+(secret|password)\b", re.I), "changing the enable secret"),
    (re.compile(r"^\s*no\s+aaa\b", re.I), "removing AAA configuration"),
    (re.compile(r"^\s*no\s+ip\s+ssh\b", re.I), "disabling SSH"),
    (re.compile(r"^\s*no\s+line\s+vty\b", re.I), "removing VTY lines"),
    (re.compile(r"^\s*crypto\s+key\s+zeroize\b", re.I), "destroying crypto keys"),
    (re.compile(r"^\s*(no\s+)?service\s+password-recovery\b", re.I), "password recovery changes"),
    (re.compile(r"^\s*config-register\b", re.I), "changing the configuration register"),
)


class CommandNotAllowedError(ValueError):
    """Raised when a requested command violates the server guardrails."""


def _reject_separators(command: str, kind: str) -> None:
    if _COMMAND_SEPARATORS.search(command):
        raise CommandNotAllowedError(
            f"{kind} may not contain command separators or shell metacharacters "
            "(; & ` $ < > or newlines)."
        )


def validate_show_command(command: str) -> str:
    """Return a normalised, read-only ``show`` command or raise.

    Only a single ``show`` command is accepted. Pipe modifiers are limited to the
    output filters in :data:`ALLOWED_PIPE_MODIFIERS` so the caller cannot write
    files to the device.
    """
    if not isinstance(command, str) or not command.strip():
        raise CommandNotAllowedError("A non-empty command string is required.")

    normalised = command.strip()
    if len(normalised) > MAX_COMMAND_LENGTH:
        raise CommandNotAllowedError(f"Command exceeds the {MAX_COMMAND_LENGTH} character limit.")

    _reject_separators(normalised, "Show commands")

    head, sep, tail = normalised.partition("|")
    if head.split()[0].lower() not in {"show", "sh"}:
        raise CommandNotAllowedError(
            "Only read-only 'show ...' commands are permitted by this tool."
        )

    if sep:
        if "|" in tail:
            raise CommandNotAllowedError("Only one pipe modifier is permitted.")
        modifier_tokens = tail.strip().split()
        if not modifier_tokens:
            raise CommandNotAllowedError("A pipe must be followed by a modifier.")
        modifier = modifier_tokens[0].lower()
        if modifier not in ALLOWED_PIPE_MODIFIERS:
            allowed = ", ".join(sorted(ALLOWED_PIPE_MODIFIERS))
            raise CommandNotAllowedError(
                f"Pipe modifier '{modifier}' is not allowed. Permitted modifiers: {allowed}."
            )

    return normalised


def validate_config(config: str) -> list[str]:
    """Return the configuration split into vetted lines, or raise.

    Lines matching :data:`_DESTRUCTIVE_CONFIG_PATTERNS` are rejected outright so an
    LLM cannot take a device offline or tamper with credentials.
    """
    if not isinstance(config, str) or not config.strip():
        raise CommandNotAllowedError("A non-empty configuration block is required.")

    lines = [line.rstrip() for line in config.splitlines() if line.strip()]
    if not lines:
        raise CommandNotAllowedError("A non-empty configuration block is required.")
    if len(lines) > MAX_CONFIG_LINES:
        raise CommandNotAllowedError(f"Configuration exceeds the {MAX_CONFIG_LINES} line limit.")

    for line in lines:
        for pattern, reason in _DESTRUCTIVE_CONFIG_PATTERNS:
            if pattern.search(line):
                raise CommandNotAllowedError(
                    f"Refusing to apply {line.strip()!r}: {reason} is blocked by this server."
                )

    return lines


def truncate(output: str, limit: int) -> str:
    """Clamp device output so a single reply cannot exhaust the model context."""
    if len(output) <= limit:
        return output
    return output[:limit] + f"\n\n... output truncated at {limit} characters ..."
