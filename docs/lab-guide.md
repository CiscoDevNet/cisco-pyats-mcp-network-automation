<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Lab guide: AI-driven network operations with VS Code, Copilot, MCP, CML and pyATS

**Goal.** Build the full environment end to end so you can drive **pyATS/Unicon**
actions against **Cisco CML** routers from **GitHub Copilot Chat** in **VS Code**,
using natural language.

**What you will have at the end**

- A Python environment with pyATS and the MCP SDK installed
- A credential-free pyATS testbed describing your CML device
- The MCP server from this repository running under VS Code
- Copilot Chat calling real network tools on your behalf

**Reference topology used throughout.** Addresses below use the
[RFC 5737](https://datatracker.ietf.org/doc/html/rfc5737) documentation ranges.
Substitute your own.

| Role | Example address | Notes |
|---|---|---|
| Linux workstation | `192.0.2.5` | Ubuntu 22.04+ or WSL 2 |
| CML router `iosv-0` | `192.0.2.10` | IOSv node with SSH enabled |

> **Before you start.** Confirm you can SSH from the workstation to the router
> manually. Every later step depends on it.

---

## 1. Prerequisites

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git openssh-client
```

Confirm reachability and SSH:

```bash
ping -c 3 192.0.2.10
ssh <router_user>@192.0.2.10
```

If SSH works, continue. If it does not, fix that first — nothing downstream can
succeed without it.

> pyATS is supported on Linux and macOS. On Windows, do all of this inside
> [WSL 2](https://learn.microsoft.com/windows/wsl/install).

---

## 2. Clone the repository and create a virtual environment

```bash
git clone https://github.com/CiscoDevNet/cisco-pyats-mcp-network-automation.git
cd cisco-pyats-mcp-network-automation

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Keeping a virtual environment inside the project folder means the MCP client can
point at one predictable interpreter path.

---

## 3. Install pyATS and the MCP SDK

```bash
pip install -r requirements.txt
```

This installs `pyats[library]` — which brings in the Genie libraries and Unicon —
along with the MCP Python SDK.

Validate:

```bash
pyats version
python -c "import pyats, mcp; print('pyATS and MCP OK')"
```

---

## 4. Create the testbed

```bash
cp testbed/testbed.example.yaml testbed/testbed.yaml
```

Open `testbed/testbed.yaml`. It looks like this:

```yaml
testbed:
  name: cml-lab
  credentials:
    default:
      username: "%ENV{CML_DEVICE_USERNAME}"
      password: "%ENV{CML_DEVICE_PASSWORD}"

devices:
  iosv-0:
    os: ios
    type: router
    connections:
      cli:
        protocol: ssh
        ip: "%ENV{CML_DEVICE_IP}"
        port: 22
```

Two things matter here:

1. **`%ENV{...}` is pyATS markup.** pyATS substitutes the named environment variable
   when the testbed loads, so no password is ever written to disk in the repository.
2. **The device key must match the name you use in prompts.** If your CML node is
   called `core-01`, rename `iosv-0` to `core-01`.

`testbed/testbed.yaml` is git-ignored, so your lab details stay local.

Validate the file:

```bash
pyats validate testbed testbed/testbed.yaml
```

---

## 5. Supply credentials through the environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
CML_DEVICE_IP=192.0.2.10
CML_DEVICE_USERNAME=cisco
CML_DEVICE_PASSWORD=<your lab password>
PYATS_TESTBED=/home/<you>/cisco-pyats-mcp-network-automation/testbed/testbed.yaml
```

Enter the IP address on its own: no `https://` prefix, no port, no trailing slash.

Load the variables into your shell:

```bash
set -a; source .env; set +a
```

`.env` is git-ignored. Never commit it.

---

## 6. Pre-flight check

```bash
python scripts/check_env.py
```

Expected output:

```text
Python           : 3.12.3 (/home/you/cisco-pyats-mcp-network-automation/.venv/bin/python)
module mcp       : OK
module pyats     : OK
module genie     : OK
module unicon    : OK
testbed          : /home/you/.../testbed/testbed.yaml (found)
CML_DEVICE_USERNAME: set
CML_DEVICE_PASSWORD: set
allow_config     : False
allow_save       : False
strict host keys : True

Environment looks good.
```

Anything reported as a problem is explained with the command that fixes it.

---

## 7. Prove pyATS connectivity without MCP

This is the single most useful troubleshooting step in the whole lab. If it works,
pyATS, the testbed and your credentials are all correct, and any later failure is an
MCP or VS Code problem.

```bash
python scripts/run_show.py --device iosv-0 --command "show ip interface brief"
```

You should see the interface table printed to your terminal.

Run it with no arguments to see the usage text:

```bash
python scripts/run_show.py
```

---

## 8. Optional: SSH keys instead of passwords

Key-based authentication avoids passwords in the environment altogether.

```bash
ssh-keygen -t ed25519 -C "pyats-mcp"
ssh-copy-id <router_user>@192.0.2.10
ssh <router_user>@192.0.2.10 "show version | include IOS"
```

Some IOSv images do not support `ssh-copy-id` cleanly; paste the public key into the
device configuration manually in that case. Password authentication is acceptable
for a throwaway lab.

---

## 9. Configure VS Code to launch the MCP server

VS Code reads MCP server definitions from `.vscode/mcp.json`.

```bash
cp .vscode/mcp.json.example .vscode/mcp.json
```

The template:

```json
{
  "inputs": [
    {
      "id": "device-password",
      "type": "promptString",
      "description": "Password for the Cisco lab device (used by pyATS)",
      "password": true
    }
  ],
  "servers": {
    "cisco-pyats-mcp": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "mcp_server"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYATS_TESTBED": "${workspaceFolder}/testbed/testbed.yaml",
        "CML_DEVICE_IP": "192.0.2.10",
        "CML_DEVICE_USERNAME": "cisco",
        "CML_DEVICE_PASSWORD": "${input:device-password}",
        "PYATS_MCP_ALLOW_CONFIG": "false"
      }
    }
  }
}
```

Update `CML_DEVICE_IP` and `CML_DEVICE_USERNAME` to match your lab. The password is
requested in a masked prompt when the server starts, so it never lands on disk.

On Windows, change `command` to `${workspaceFolder}\\.venv\\Scripts\\python.exe`.

See [mcp-config-explained.md](mcp-config-explained.md) for a field-by-field
walkthrough.

### 9.1 Open the workspace

```bash
code .
```

### 9.2 Install the Copilot extensions

From the Extensions view, install **GitHub Copilot** and **GitHub Copilot Chat**,
then sign in to GitHub.

### 9.3 Trust the server

VS Code asks you to trust an MCP server because it executes local code. Only trust
servers you have read. The code for this one is in
[../mcp_server/](../mcp_server/).

---

## 10. Use the tools from Copilot Chat

Open Copilot Chat, switch to **Agent** mode, and confirm `cisco-pyats-mcp` appears
in the tools picker.

### 10.1 Discover devices

- *"Which devices are available through the pyATS MCP server?"*

### 10.2 Run a show command

- *"Run `show ip interface brief` on iosv-0 and tell me which interfaces are down."*

### 10.3 Run a health check

- *"Do a detailed health check on iosv-0 and summarise anything abnormal."*

### 10.4 Back up a configuration

- *"Back up the running configuration of iosv-0 and tell me whether every interface
  has a description."*

VS Code shows each tool invocation for approval before it runs. Read what it is
about to do rather than approving reflexively.

---

## 11. Optional: enable configuration changes

Configuration is disabled by default. Turn it on only against a lab device you own,
and scope it to that device:

```bash
export PYATS_MCP_ALLOW_CONFIG=true
export PYATS_MCP_ALLOWED_DEVICES=iosv-0
```

Or set the same variables in the `env` block of `.vscode/mcp.json`, then restart the
server from the MCP servers view.

Ask Copilot to apply this loopback to `iosv-0`:

```text
interface loopback123
 description created-by-copilot-mcp
 ip address 10.123.123.1 255.255.255.255
```

Then verify with a read-only call:

- *"Run `show ip interface brief | include Loopback123` on iosv-0."*

The server rejects destructive lines — `reload`, `write erase`, `erase`, `format`,
`delete`, `boot system`, `config-register`, `crypto key zeroize`, local `username`
changes and `no ip ssh` — even when configuration is enabled.

---

## 12. Test checklist

| # | Test | How | Pass criteria |
|---|---|---|---|
| A | Environment | `python scripts/check_env.py` | "Environment looks good." |
| B | pyATS connectivity | `python scripts/run_show.py -d iosv-0 -c "show version"` | Device output printed |
| C | Guardrails | `pytest -q` | All tests pass |
| D | MCP discovery | Ask Copilot to list devices | Device names returned |
| E | Read-only tool | Ask for `show ip interface brief` | Interface table returned |
| F | Guardrail enforcement | Ask Copilot to run `reload` on the device | Tool refuses the request |
| G | Config change (opt in) | Apply the loopback above, then verify | Loopback appears as up/up |

---

## 13. Troubleshooting

### Tools do not appear in Copilot Chat

- Confirm `.vscode/mcp.json` is valid JSON.
- Confirm the interpreter path exists:
  `ls -l .venv/bin/python`
- Use absolute paths, or `${workspaceFolder}` which VS Code expands to one.
- Open the **Output** panel and select the MCP server channel to read start-up
  errors.

### Authentication failed

- Reproduce outside pyATS: `ssh <router_user>@192.0.2.10`
- Confirm the variables are actually set in the environment the server runs in —
  variables exported in your terminal are not visible to a server VS Code launched
  before you exported them. Restart the server after changing them.
- Remember the testbed reads `%ENV{CML_DEVICE_USERNAME}` and
  `%ENV{CML_DEVICE_PASSWORD}`; a typo in the variable name yields an empty
  credential.

### Server starts, then disconnects

MCP stdio servers must never write to stdout — it carries the protocol frames. Never
add `print()` to the server; use `logging`, which this project sends to stderr. Every
device connection is opened with `log_stdout=False` for the same reason.

### Host key verification failed

The server enables SSH host key checking by default. Either add the device to your
`known_hosts` by connecting once manually, point `PYATS_MCP_KNOWN_HOSTS` at a
dedicated file, or — for a throwaway lab only — set `PYATS_MCP_INSECURE_SSH=true`.

### Testbed not found

`PYATS_TESTBED` must be an absolute path when the server is launched by VS Code,
because the working directory may differ from your terminal's.

---

## 14. Where to go next

- Add more devices to `testbed/testbed.yaml`; no code changes are needed.
- Add a new read-only tool — see the checklist in
  [../CONTRIBUTING.md](../CONTRIBUTING.md).
- Explore the pyATS CLI in [pyats-cli-cheatsheet.md](pyats-cli-cheatsheet.md),
  especially `pyats learn` and `pyats diff` for pre/post change comparison.
- Read [../SECURITY.md](../SECURITY.md) before using this anywhere beyond a lab.

---

## Appendix: quick verification one-liner

```bash
source .venv/bin/activate && \
  python scripts/check_env.py && \
  python scripts/run_show.py -d iosv-0 -c "show version | include IOS"
```
