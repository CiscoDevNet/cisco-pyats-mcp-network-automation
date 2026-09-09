<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# AGENTS.md

Guidance for coding agents (VS Code / GitHub Copilot, Cursor, Codex, Gemini CLI, etc.)
working in this repository.

## Project overview

This repository is a **Model Context Protocol (MCP) server** that exposes a deliberately
narrow set of **Cisco pyATS** operations as tools an AI assistant can call. An engineer
asks a question in natural language, the assistant calls a vetted tool, and the server
validates the request before it reaches a Cisco IOS / IOS XE device over SSH.

The server is **read-only by default**. Configuration changes are opt-in through
environment variables, and service-impacting commands are blocked outright.

| Path | Responsibility |
|---|---|
| `mcp_server/server.py` | FastMCP tool definitions (`list_devices`, `run_show_command`, `health_check`, `backup_running_config`, `apply_config`) |
| `mcp_server/validation.py` | Guardrails: `show` allow-list, destructive-command deny-list, injection guards, output truncation |
| `mcp_server/config.py` | `Settings.from_env()` — all runtime configuration, safe defaults |
| `mcp_server/devices.py` | Testbed loading and short-lived pyATS connections (context manager) |
| `scripts/check_env.py` | Pre-flight environment validator |
| `scripts/run_show.py` | Run a `show` command without MCP, for isolating connectivity issues |
| `tests/` | Guardrail and settings tests — no device, no pyATS install required |
| `testbed/testbed.example.yaml` | Credential-free testbed template using pyATS `%ENV{}` markup |

### There is no OpenAPI spec for this project

This server drives devices over the **CLI via SSH** (pyATS/Unicon), not a REST API.
Do not look for or generate an OpenAPI document. Use the pyATS, Genie and MCP references
in [Reference documentation and SDKs](#reference-documentation-and-sdks) instead.

## Golden rules (do not break these)

1. **Never write to stdout from `mcp_server/`.** The MCP stdio transport reserves stdout
   for protocol frames. Log to stderr (`logging.basicConfig(stream=sys.stderr, ...)`) and
   keep `device.connect(log_stdout=False)`. A stray `print()` corrupts the session.
2. **Never weaken the guardrails.** Every device-bound string must pass through
   `validate_show_command()` or `validate_config()`. Do not widen
   `ALLOWED_PIPE_MODIFIERS`, relax `_COMMAND_SEPARATORS`, or remove entries from
   `_DESTRUCTIVE_CONFIG_PATTERNS` without an explicit request and a matching test.
3. **Keep writes opt-in.** `apply_config` must stay gated on `PYATS_MCP_ALLOW_CONFIG`, and
   `write memory` additionally on `PYATS_MCP_ALLOW_SAVE`. Defaults stay `false`.
4. **Never commit secrets.** No IPs, usernames, passwords or enable secrets in code, tests,
   docs or examples. Use `%ENV{}` in the testbed and RFC 5737 documentation addresses
   (`192.0.2.0/24`) in examples. `.env`, `testbed/testbed.yaml` and `.vscode/mcp.json` are
   git-ignored — never add them.
5. **Tests must run without pyATS and without a device.** CI installs only
   `pytest ruff bandit`. Import `pyats` lazily inside functions (see `devices.py`) or under
   `TYPE_CHECKING`; never at module import time in code the tests reach.
6. **New device connections go through `connected_device()`** so the session is always
   closed and a failed command never leaves a VTY line pinned.
7. **Every new file needs a REUSE/SPDX header** (see [Contribution conventions](#contribution-conventions)).

## Dev environment tips

- **Python version**: 3.10 or later (`requires-python = ">=3.10"`). CI runs 3.10–3.13.
- **Windows**: pyATS is supported on Linux and macOS. Use
  [WSL 2](https://learn.microsoft.com/windows/wsl/install) for anything that connects to a
  device. Windows-native Python is fine for linting and the unit tests.
- **Virtual env**:

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
  python -m pip install -U pip setuptools wheel
  pip install -r requirements.txt        # mcp + pyats[library]
  pip install -r requirements-dev.txt    # adds pytest, ruff, bandit
  ```

- **Lab configuration** (never edit the tracked examples in place):

  ```bash
  cp testbed/testbed.example.yaml testbed/testbed.yaml
  cp .env.example .env
  cp .vscode/mcp.json.example .vscode/mcp.json
  ```

- **Load credentials**: `set -a; source .env; set +a` (Linux/macOS/WSL). Enter the
  management IP on its own — no `https://` prefix, no trailing slash.
- **Pre-flight check** before debugging anything else: `python scripts/check_env.py`.

### Quick run examples

```bash
# Validate the environment: imports, testbed resolution, credential variables.
python scripts/check_env.py

# Validate the testbed file itself.
pyats validate testbed testbed/testbed.yaml

# Prove connectivity without MCP in the loop (fastest way to isolate a failure).
python scripts/run_show.py --device iosv-0 --command "show ip interface brief"

# Run the MCP server over stdio. Normally VS Code launches this for you.
python -m mcp_server
```

### Configuration reference

All settings come from the environment, so the same code runs in a lab, in CI, or under an
MCP client without edits.

| Variable | Default | Purpose |
|---|---|---|
| `PYATS_TESTBED` | `testbed/testbed.yaml` | Testbed path. Use an absolute path from an MCP client. |
| `PYATS_MCP_ALLOW_CONFIG` | `false` | Master switch for `apply_config`. |
| `PYATS_MCP_ALLOW_SAVE` | `false` | Additionally required for `write memory`. |
| `PYATS_MCP_ALLOWED_DEVICES` | *(empty)* | Comma-separated device allow-list. Empty means the whole testbed. |
| `PYATS_MCP_CONNECT_TIMEOUT` | `60` | SSH connect timeout, seconds. |
| `PYATS_MCP_COMMAND_TIMEOUT` | `120` | Per-command timeout, seconds. |
| `PYATS_MCP_MAX_OUTPUT_CHARS` | `60000` | Caps a tool response so long output cannot exhaust the model context. |
| `PYATS_MCP_INSECURE_SSH` | `false` | Disables SSH host key verification. Throwaway labs only. |
| `PYATS_MCP_KNOWN_HOSTS` | *(system default)* | Custom `known_hosts` file. |

Device credentials are consumed by the testbed, not by the code: `CML_DEVICE_IP`,
`CML_DEVICE_USERNAME`, `CML_DEVICE_PASSWORD`, `CML_DEVICE_ENABLE_PASSWORD`.

## MCP servers

### The server in this repository

Client configuration lives in `.vscode/mcp.json` (copy from `.vscode/mcp.json.example`).
It is a **stdio** server started as `python -m mcp_server`, and the device password is
supplied through a VS Code `promptString` input so it is never written to disk.
Set `command` to the interpreter inside your virtual environment:

- Linux / macOS / WSL: `${workspaceFolder}/.venv/bin/python`
- Windows: `${workspaceFolder}\\.venv\\Scripts\\python.exe`

Reload VS Code, open Copilot Chat in **Agent** mode, and confirm `cisco-pyats-mcp` appears
in the tools picker. See [docs/mcp-config-explained.md](docs/mcp-config-explained.md) for a
field-by-field walkthrough.

Tools exposed to the assistant:

| Tool | Changes device state | Description |
|---|---|---|
| `list_devices` | No | Testbed devices this server may reach |
| `run_show_command` | No | One validated `show` command |
| `health_check` | No | `basic` or `detailed` read-only snapshot |
| `backup_running_config` | No | `show running-config` for backup or diffing |
| `apply_config` | **Yes** | Gated on `PYATS_MCP_ALLOW_CONFIG=true` |

### Useful MCP servers when working on this repo

- **GitHub MCP server** — issues, pull requests and code search:
  <https://github.com/github/github-mcp-server>
- **Context7 / documentation MCP servers** — for pulling current pyATS and MCP SDK docs
  into context instead of guessing API shapes.

Do not add an MCP server to the repository configuration without asking; `.vscode/mcp.json`
is git-ignored and is the developer's own file.

## Testing instructions

The guardrail and settings tests need **no device and no pyATS installation** — that is
deliberate, so agents and CI can validate changes offline.

```bash
pip install -r requirements-dev.txt
pytest -q                        # 44 tests
ruff check .                     # lint
ruff format --check .            # CI fails on unformatted code; run `ruff format .` to fix
bandit -r mcp_server scripts -q  # security scan
```

CI (`.github/workflows/ci.yml`) runs exactly those four steps on Python 3.10, 3.11, 3.12
and 3.13. Run all four locally before proposing a change.

Add a test to `tests/test_validation.py` for **any** change to the allow-list or deny-list,
and to `tests/test_config.py` for any new setting.

### Test against real devices

- **Cisco DevNet Sandbox** — reserve or use an always-on IOS XE sandbox, then put its
  address and credentials in `.env` and point `testbed/testbed.yaml` at it:
  <https://devnetsandbox.cisco.com/DevNet> (catalogue: <https://developer.cisco.com/site/sandbox/>).
  On a shared sandbox keep `PYATS_MCP_ALLOW_CONFIG=false` so the server stays read-only.
- **Cisco Modeling Labs** — the IOSv topology used throughout the lab guide:
  <https://developer.cisco.com/modeling-labs/>. Build instructions:
  [docs/lab-guide.md](docs/lab-guide.md).

## Reference documentation and SDKs

| Component | Version pinned here | Reference |
|---|---|---|
| Cisco pyATS + Genie (`pyats[library]`) | `>=24.0` | <https://developer.cisco.com/pyats/> · docs: <https://developer.cisco.com/docs/pyats/> · source: <https://github.com/CiscoTestAutomation/pyats> |
| Genie parsers | ships with `pyats[library]` | <https://github.com/CiscoTestAutomation/genieparser> |
| Unicon (connection library) | ships with `pyats[library]` | <https://github.com/CiscoTestAutomation/unicon.plugins> |
| MCP Python SDK (`mcp`, FastMCP) | `>=1.2.0` | <https://modelcontextprotocol.io/> · <https://github.com/modelcontextprotocol/python-sdk> |
| VS Code MCP client | VS Code + Copilot Chat | <https://code.visualstudio.com/docs/copilot/chat/mcp-servers> |
| Cisco API documentation | — | <https://developer.cisco.com/docs/> |

In-repo documentation, which agents should read before changing behaviour:

- [docs/lab-guide.md](docs/lab-guide.md) — end-to-end lab build (CML, pyATS, VS Code).
- [docs/server-code-explained.md](docs/server-code-explained.md) — the server code, line by line.
- [docs/mcp-config-explained.md](docs/mcp-config-explained.md) — every `mcp.json` field, plus troubleshooting.
- [docs/pyats-cli-cheatsheet.md](docs/pyats-cli-cheatsheet.md) — everyday pyATS and Genie commands.
- [SECURITY.md](SECURITY.md) — guardrails, operator responsibilities, vulnerability reporting.

## PR instructions

- **Security**: do not commit real credentials, tokens, IP addresses or hostnames. Use
  placeholders and document any required environment variables or files. Security bugs go
  through [SECURITY.md](SECURITY.md), **not** a public GitHub issue.
- **Before opening a PR**, run `pytest -q`, `ruff check .`, `ruff format --check .` and
  `bandit -r mcp_server scripts -q`.
- **Tests are expected** for any change in behaviour, especially guardrail changes.
- **Update the docs** alongside the code: a new setting belongs in `README.md`, `.env.example`
  and the table above; a new tool belongs in `README.md` and `docs/server-code-explained.md`.
- **Update [CHANGELOG.md](CHANGELOG.md)** for user-visible changes. The project follows
  semantic versioning; breaking changes may be held for the next major release.
- Fill in `.github/pull_request_template.md` and keep PRs focused on one concern.

## Contribution conventions

- **Backward compatibility**: do not change existing behaviour unless it is clearly a fix or
  an improvement, and document it. Renaming or removing an MCP tool, or changing a tool's
  parameters, is a breaking change for every user's `mcp.json`.
- **Style**: ruff with `line-length = 100`, `target-version = "py310"`, rule set
  `E, F, W, I, B, UP, S` (see `pyproject.toml`). Use `from __future__ import annotations`,
  type hints on public functions, and concise docstrings in the existing voice.
- **Licensing (REUSE/SPDX)**: every new file needs a header matching the repository style —

  ```python
  # Copyright 2026 Cisco Systems, Inc. and its affiliates
  #
  # SPDX-License-Identifier: Apache-2.0
  ```

  Use the comment syntax of the file type, or a `.license` sidecar for formats that cannot
  carry comments (for example JSON). Do not edit `LICENSE`, `LICENSES/` or third-party
  records in `NOTICE`.
- **Safety first**: this project is intended for **lab environments**, not production
  networks. When in doubt, choose the more restrictive option and make the permissive one
  opt-in.
