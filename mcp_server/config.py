# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0
"""Runtime settings for the pyATS MCP server, resolved from environment variables.

No credentials are stored here. Device credentials are resolved by pyATS from the
testbed file, which itself should reference environment variables (``%ENV{...}``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_TESTBED_PATH = "testbed/testbed.yaml"
DEFAULT_CONNECT_TIMEOUT = 60
DEFAULT_COMMAND_TIMEOUT = 120
DEFAULT_MAX_OUTPUT_CHARS = 60_000

_TRUTHY = frozenset({"1", "true", "yes", "on"})


class ConfigError(RuntimeError):
    """Raised when the server is started with an unusable configuration."""


def _as_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in _TRUTHY


def _as_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be greater than zero, got {value}")
    return value


def _as_frozenset(name: str) -> frozenset[str]:
    raw = os.environ.get(name, "")
    return frozenset(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    """Immutable view of the server configuration."""

    testbed_path: str = DEFAULT_TESTBED_PATH
    allow_config: bool = False
    allow_save: bool = False
    allowed_devices: frozenset[str] = frozenset()
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT
    command_timeout: int = DEFAULT_COMMAND_TIMEOUT
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS
    strict_host_key_checking: bool = True
    known_hosts_file: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the process environment."""
        return cls(
            testbed_path=os.environ.get("PYATS_TESTBED", DEFAULT_TESTBED_PATH),
            allow_config=_as_bool("PYATS_MCP_ALLOW_CONFIG", False),
            allow_save=_as_bool("PYATS_MCP_ALLOW_SAVE", False),
            allowed_devices=_as_frozenset("PYATS_MCP_ALLOWED_DEVICES"),
            connect_timeout=_as_int("PYATS_MCP_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT),
            command_timeout=_as_int("PYATS_MCP_COMMAND_TIMEOUT", DEFAULT_COMMAND_TIMEOUT),
            max_output_chars=_as_int("PYATS_MCP_MAX_OUTPUT_CHARS", DEFAULT_MAX_OUTPUT_CHARS),
            strict_host_key_checking=not _as_bool("PYATS_MCP_INSECURE_SSH", False),
            known_hosts_file=os.environ.get("PYATS_MCP_KNOWN_HOSTS") or None,
        )

    def ssh_options(self) -> str:
        """Return the ``ssh`` options Unicon should use when opening the CLI session."""
        if not self.strict_host_key_checking:
            return "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        options = "-o StrictHostKeyChecking=yes"
        if self.known_hosts_file:
            options += f" -o UserKnownHostsFile={self.known_hosts_file}"
        return options

    def device_is_allowed(self, device: str) -> bool:
        """Return ``True`` when *device* may be reached through this server."""
        return not self.allowed_devices or device in self.allowed_devices
