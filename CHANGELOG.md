# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-17

First release prepared for submission to Cisco Code Exchange.

### Added

- Runnable MCP server package `mcp_server` exposing five pyATS-backed tools:
  `list_devices`, `run_show_command`, `health_check`, `backup_running_config`
  and `apply_config`.
- Guardrail module with a `show` command allow-list, command-injection rejection
  and a destructive-configuration deny-list.
- Environment-driven settings with safe defaults: configuration changes and
  startup-config saves are disabled, SSH host key verification is enabled.
- `scripts/check_env.py` pre-flight validator and `scripts/run_show.py` CLI, both
  with `--help` output.
- Credential-free testbed template using the pyATS `%ENV{}` markup, plus
  `.env.example` and `.vscode/mcp.json.example`.
- Unit tests for guardrails and settings that run without pyATS or a device.
- GitHub Actions workflow running ruff, pytest and bandit on Python 3.10-3.13.
- `NOTICE`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue and
  pull request templates.

### Changed

- README rewritten to follow the Cisco Code Exchange repository template.
- Walkthrough documents moved into `docs/` with descriptive names.
- Hard-coded lab IP addresses replaced with RFC 5737 documentation addresses.
