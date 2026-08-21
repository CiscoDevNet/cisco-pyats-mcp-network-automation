# The MCP client configuration explained

This is a beginner-friendly walkthrough of `.vscode/mcp.json` — the file that tells
VS Code how to start the MCP server in this repository.

It is **not** a Python script. It is **JSON configuration**. Think of it as a remote
control:

- **command** — which program to run
- **args** — what to run with it
- **env** — extra settings handed to that program
- **inputs** — values VS Code asks you for at start-up

---

## The configuration

`.vscode/mcp.json.example` in this repository:

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
        "PYATS_MCP_ALLOW_CONFIG": "false",
        "PYATS_MCP_ALLOW_SAVE": "false",
        "PYATS_MCP_INSECURE_SSH": "false"
      }
    }
  }
}
```

Copy it to `.vscode/mcp.json` before editing. The copy is git-ignored, so your lab
details never leave your machine.

---

## Every field, one at a time

### `inputs`

A list of values VS Code prompts you for when the server starts.

- `id` — the name you refer to later with `${input:device-password}`
- `type: promptString` — show a text box
- `password: true` — mask the typing and keep the value out of settings files

**Why it matters.** Without this, the device password would have to be written into
a file. With it, the password lives only in memory for the session. This is the
single most important security feature of the configuration.

### `servers`

The section holding one or more MCP servers. Each key is a server name of your
choosing; the name is what appears in the Copilot Chat tools picker.

> Some MCP clients — Claude Desktop for example — use `mcpServers` instead of
> `servers`. The inner fields are the same.

### `type: "stdio"`

How VS Code talks to the server: by launching it as a child process and exchanging
messages over standard input and output.

This is why the server must never `print()` to stdout. Stdout carries the protocol.
Anything else written there corrupts the conversation and the server disconnects.

### `command`

The exact Python interpreter to use.

A machine usually has several Python installations. This path points at the one
inside the project's virtual environment, which is the only one with pyATS and the
MCP SDK installed.

- Linux / macOS / WSL: `${workspaceFolder}/.venv/bin/python`
- Windows: `${workspaceFolder}\\.venv\\Scripts\\python.exe`

`${workspaceFolder}` is a VS Code variable that expands to the folder you opened, so
the file works for anyone who clones the repository.

Check the path exists:

```bash
ls -l .venv/bin/python
```

### `args`

The arguments passed to `command`. Here they are `["-m", "mcp_server"]`, so VS Code
effectively runs:

```bash
/path/to/.venv/bin/python -m mcp_server
```

`-m` runs the `mcp_server` package, which executes
[`mcp_server/__main__.py`](../mcp_server/__main__.py). Running a package rather than
a file path means imports inside the package resolve correctly.

### `cwd`

The working directory for the server process. Setting it to `${workspaceFolder}`
makes relative paths behave the way they do in your terminal.

### `env`

Environment variables given to the server process. These are simple key/value
settings the program reads at runtime.

| Variable | Read by | Purpose |
|---|---|---|
| `PYATS_TESTBED` | the server | Where the testbed YAML lives |
| `CML_DEVICE_IP` | the testbed, via `%ENV{}` | Device management address |
| `CML_DEVICE_USERNAME` | the testbed, via `%ENV{}` | Login username |
| `CML_DEVICE_PASSWORD` | the testbed, via `%ENV{}` | Login password, from the prompt |
| `PYATS_MCP_ALLOW_CONFIG` | the server | Master switch for configuration changes |
| `PYATS_MCP_ALLOW_SAVE` | the server | Second switch, required for `write memory` |
| `PYATS_MCP_INSECURE_SSH` | the server | Disables SSH host key checking when `true` |

The full list is in the Configuration table of the
[README](../README.md#configuration-optional).

---

## What happens when the server starts

1. VS Code prompts you for the device password.
2. It launches `/path/to/.venv/bin/python -m mcp_server` with the `env` values set.
3. `mcp_server` reads its settings from those variables.
4. pyATS loads `testbed.yaml` and substitutes `%ENV{CML_DEVICE_PASSWORD}` with the
   value you typed.
5. VS Code asks the server which tools it offers, and they appear in Copilot Chat.

---

## Patterns worth copying

### Pin the interpreter

Pointing at a virtual environment's Python makes runs reproducible: the same
dependencies, every time, on every machine. In your own projects, achieve this with
virtual environments plus `requirements.txt` or `pyproject.toml`.

### Keep configuration out of code

Paths, addresses and switches are supplied by environment variables rather than
hard-coded. The same code then runs in a lab, in CI and under an MCP client without
edits.

### Keep secrets out of configuration too

`${input:...}` is the step beyond that. Configuration files get committed by
accident; a runtime prompt cannot be.

### Separate the runner from the logic

`mcp.json` is the **runner** — how to start things.
[`mcp_server/server.py`](../mcp_server/server.py) is the **logic** — what actually
happens. Keeping them apart makes both easier to change.

---

## Common mistakes

### Wrong interpreter path

The most frequent failure. Verify each path:

```bash
ls -l .venv/bin/python
ls -l testbed/testbed.yaml
```

### Variables set in the wrong place

Exporting a variable in your terminal does **not** affect a server VS Code already
launched. Either put the value in the `env` block, or restart the server after
changing your environment.

### Missing packages

If the server starts and then reports "module not found", the interpreter in
`command` is not the one where you installed the dependencies:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Invalid JSON

A trailing comma or an unescaped backslash in a Windows path breaks the file. VS Code
underlines the error in the editor. Windows paths need doubled backslashes:
`C:\\Users\\you\\project\\.venv\\Scripts\\python.exe`.

### Testbed not found

Use an absolute path, or `${workspaceFolder}/...`. The server's working directory is
not necessarily your terminal's.

---

## Where to look when it still does not work

Open the **Output** panel in VS Code and select the channel for the MCP server. The
server logs its start-up settings there, including which testbed it loaded and
whether write operations are enabled.

Then work through the troubleshooting section of the
[lab guide](lab-guide.md#13-troubleshooting).
