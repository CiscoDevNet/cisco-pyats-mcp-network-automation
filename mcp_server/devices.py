# Copyright (c) 2026 Ranil Fernando
# SPDX-License-Identifier: Apache-2.0
"""Thin pyATS wrapper: testbed loading and short-lived device connections."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from .config import ConfigError, Settings

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from pyats.topology import Testbed

logger = logging.getLogger(__name__)


class DeviceNotAllowedError(ValueError):
    """Raised when the requested device is unknown or outside the allow-list."""


def load_testbed(settings: Settings) -> Testbed:
    """Load the pyATS testbed referenced by the current settings."""
    from pyats.topology import loader

    path = Path(settings.testbed_path).expanduser()
    if not path.is_file():
        raise ConfigError(
            f"Testbed file not found at '{path}'. Set PYATS_TESTBED to an absolute path "
            "or copy testbed/testbed.example.yaml to testbed/testbed.yaml."
        )
    return loader.load(str(path))


def list_device_names(settings: Settings) -> list[str]:
    """Return the device names this server is permitted to reach."""
    testbed = load_testbed(settings)
    return sorted(name for name in testbed.devices if settings.device_is_allowed(name))


@contextmanager
def connected_device(settings: Settings, device_name: str) -> Iterator[object]:
    """Yield a connected pyATS device and always disconnect afterwards."""
    if not settings.device_is_allowed(device_name):
        raise DeviceNotAllowedError(f"Device '{device_name}' is not in PYATS_MCP_ALLOWED_DEVICES.")

    testbed = load_testbed(settings)
    if device_name not in testbed.devices:
        known = ", ".join(sorted(testbed.devices)) or "<none>"
        raise DeviceNotAllowedError(
            f"Unknown device '{device_name}'. Devices in the testbed: {known}."
        )

    device = testbed.devices[device_name]
    connection = device.connections.get("cli")
    if connection is not None:
        connection.setdefault("ssh_options", settings.ssh_options())
        arguments = connection.setdefault("arguments", {})
        arguments.setdefault("connection_timeout", settings.connect_timeout)

    # log_stdout=False keeps Unicon output off stdout, which the MCP stdio
    # transport reserves for protocol frames.
    device.connect(log_stdout=False, learn_hostname=True)
    try:
        yield device
    finally:
        try:
            device.disconnect()
        except Exception:  # noqa: BLE001 - never mask the original tool error
            logger.warning("Failed to cleanly disconnect from %s", device_name, exc_info=True)
