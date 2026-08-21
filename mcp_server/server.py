# Copyright (c) 2026 Ranil Fernando
# SPDX-License-Identifier: Apache-2.0
"""MCP server exposing guarded Cisco IOS operations backed by pyATS.

Transport is MCP stdio, so stdout is reserved for protocol frames. All logging
goes to stderr.
"""

from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

from .config import ConfigError, Settings
from .devices import DeviceNotAllowedError, connected_device, list_device_names
from .validation import (
    CommandNotAllowedError,
    truncate,
    validate_config,
    validate_show_command,
)

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("cisco-pyats-mcp")

mcp = FastMCP("cisco-pyats-mcp")

BASIC_HEALTH_COMMANDS = (
    "show version",
    "show ip interface brief",
)

DETAILED_HEALTH_COMMANDS = BASIC_HEALTH_COMMANDS + (
    "show processes cpu | include one minute",
    "show memory statistics",
    "show ip route summary",
    "show logging | include %",
)


def _settings() -> Settings:
    """Read settings on every call so config changes do not require a restart."""
    return Settings.from_env()


@mcp.tool()
def list_devices() -> str:
    """List the devices in the pyATS testbed that this server may reach."""
    settings = _settings()
    names = list_device_names(settings)
    if not names:
        return "No devices available. Check PYATS_TESTBED and PYATS_MCP_ALLOWED_DEVICES."
    return "\n".join(names)


@mcp.tool()
def run_show_command(device: str, command: str) -> str:
    """Run a single read-only `show` command on a device and return its output.

    Args:
        device: Device name as defined in the pyATS testbed, for example `iosv-0`.
        command: A `show` command. Pipe modifiers are limited to
            begin/count/exclude/include/section.
    """
    settings = _settings()
    safe_command = validate_show_command(command)
    with connected_device(settings, device) as dev:
        output = dev.execute(safe_command, timeout=settings.command_timeout)
    return truncate(output, settings.max_output_chars)


@mcp.tool()
def health_check(device: str, level: str = "basic") -> str:
    """Collect a read-only health snapshot from a device.

    Args:
        device: Device name as defined in the pyATS testbed.
        level: `basic` for version and interface state, `detailed` to add CPU,
            memory, routing summary and recent logs.
    """
    settings = _settings()
    normalised = level.strip().lower()
    if normalised not in {"basic", "detailed"}:
        raise CommandNotAllowedError("level must be either 'basic' or 'detailed'.")

    commands = BASIC_HEALTH_COMMANDS if normalised == "basic" else DETAILED_HEALTH_COMMANDS
    sections: list[str] = []
    with connected_device(settings, device) as dev:
        for command in commands:
            try:
                output = dev.execute(command, timeout=settings.command_timeout)
            except Exception as exc:  # noqa: BLE001 - report per-command failures
                output = f"<command failed: {exc}>"
            sections.append(f"===== {command} =====\n{output}")
    return truncate("\n\n".join(sections), settings.max_output_chars)


@mcp.tool()
def backup_running_config(device: str) -> str:
    """Return the running configuration of a device for offline backup or diffing."""
    settings = _settings()
    with connected_device(settings, device) as dev:
        output = dev.execute("show running-config", timeout=settings.command_timeout)
    return truncate(output, settings.max_output_chars)


@mcp.tool()
def apply_config(device: str, config: str, save: bool = False) -> str:
    """Apply configuration lines to a device. Disabled unless explicitly enabled.

    Requires `PYATS_MCP_ALLOW_CONFIG=true`. Saving to startup-config additionally
    requires `PYATS_MCP_ALLOW_SAVE=true`. Service-impacting commands such as
    `reload`, `write erase` and local user changes are always rejected.

    Args:
        device: Device name as defined in the pyATS testbed.
        config: Configuration lines to apply, one per line.
        save: When true, copy running-config to startup-config afterwards.
    """
    settings = _settings()
    if not settings.allow_config:
        raise CommandNotAllowedError(
            "Configuration changes are disabled. Set PYATS_MCP_ALLOW_CONFIG=true to enable them."
        )
    if save and not settings.allow_save:
        raise CommandNotAllowedError(
            "Saving to startup-config is disabled. Set PYATS_MCP_ALLOW_SAVE=true to enable it."
        )

    lines = validate_config(config)
    logger.info("Applying %d configuration line(s) to %s (save=%s)", len(lines), device, save)

    with connected_device(settings, device) as dev:
        result = dev.configure(lines, timeout=settings.command_timeout)
        if save:
            result += "\n\n===== write memory =====\n"
            result += dev.execute("write memory", timeout=settings.command_timeout)
    return truncate(result, settings.max_output_chars)


def main() -> None:
    """Entry point used by `python -m mcp_server`."""
    try:
        settings = _settings()
    except ConfigError as exc:
        logger.error("%s", exc)
        raise SystemExit(2) from exc

    logger.info(
        "Starting cisco-pyats-mcp | testbed=%s allow_config=%s allow_save=%s strict_host_keys=%s",
        settings.testbed_path,
        settings.allow_config,
        settings.allow_save,
        settings.strict_host_key_checking,
    )
    if not settings.strict_host_key_checking:
        logger.warning(
            "SSH host key checking is DISABLED (PYATS_MCP_INSECURE_SSH). Use lab networks only."
        )
    mcp.run()


__all__ = [
    "CommandNotAllowedError",
    "DeviceNotAllowedError",
    "apply_config",
    "backup_running_config",
    "health_check",
    "list_devices",
    "main",
    "mcp",
    "run_show_command",
]
