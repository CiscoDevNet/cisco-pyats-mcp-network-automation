# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for environment-driven settings."""

from __future__ import annotations

import pytest

from mcp_server.config import ConfigError, Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "PYATS_TESTBED",
        "PYATS_MCP_ALLOW_CONFIG",
        "PYATS_MCP_ALLOW_SAVE",
        "PYATS_MCP_ALLOWED_DEVICES",
        "PYATS_MCP_CONNECT_TIMEOUT",
        "PYATS_MCP_COMMAND_TIMEOUT",
        "PYATS_MCP_MAX_OUTPUT_CHARS",
        "PYATS_MCP_INSECURE_SSH",
        "PYATS_MCP_KNOWN_HOSTS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults_are_safe() -> None:
    settings = Settings.from_env()
    assert settings.allow_config is False
    assert settings.allow_save is False
    assert settings.strict_host_key_checking is True
    assert settings.allowed_devices == frozenset()
    assert "StrictHostKeyChecking=yes" in settings.ssh_options()


def test_write_operations_can_be_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYATS_MCP_ALLOW_CONFIG", "true")
    monkeypatch.setenv("PYATS_MCP_ALLOW_SAVE", "yes")
    settings = Settings.from_env()
    assert settings.allow_config is True
    assert settings.allow_save is True


def test_device_allow_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYATS_MCP_ALLOWED_DEVICES", "iosv-0, iosv-1")
    settings = Settings.from_env()
    assert settings.device_is_allowed("iosv-0")
    assert settings.device_is_allowed("iosv-1")
    assert not settings.device_is_allowed("core-router")


def test_insecure_ssh_is_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYATS_MCP_INSECURE_SSH", "true")
    settings = Settings.from_env()
    assert settings.strict_host_key_checking is False
    assert "StrictHostKeyChecking=no" in settings.ssh_options()


def test_invalid_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYATS_MCP_COMMAND_TIMEOUT", "not-a-number")
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_negative_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYATS_MCP_CONNECT_TIMEOUT", "-5")
    with pytest.raises(ConfigError):
        Settings.from_env()
