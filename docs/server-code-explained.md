# The server code explained, step by step

A beginner-friendly walkthrough of the code in [`mcp_server/`](../mcp_server/),
written so an engineer who is new to Python can follow it and adapt it.

---

## 1. The big picture

The package is a **tool server**. It advertises a handful of functions to an AI
assistant, and when the assistant decides to call one, the server:

1. checks whether the request is allowed,
2. connects to a Cisco device with pyATS,
3. runs the command,
4. disconnects and returns the output.

It is split into four small files so each one does a single job:

| File | Job |
|---|---|
| [`config.py`](../mcp_server/config.py) | Read settings from environment variables |
| [`validation.py`](../mcp_server/validation.py) | Decide whether a command is allowed |
| [`devices.py`](../mcp_server/devices.py) | Load the testbed and manage connections |
| [`server.py`](../mcp_server/server.py) | Define the tools the assistant can call |

That separation is the most important idea in the whole project. The rules about
what is safe live in one file, with tests, instead of being scattered through the
code that talks to devices.

---

## 2. Settings: `config.py`

```python
@dataclass(frozen=True)
class Settings:
    testbed_path: str = DEFAULT_TESTBED_PATH
    allow_config: bool = False
    allow_save: bool = False
    ...
```

**What a dataclass is.** A compact way to define a class that mostly holds values.
`frozen=True` makes it read-only after creation, so no part of the program can
quietly change a safety setting at runtime.

**Where the values come from.** `Settings.from_env()` reads environment variables.
Nothing is hard-coded, and no credentials appear anywhere in this file.

**Why the defaults are what they are.** `allow_config` and `allow_save` default to
`False`, and host key checking defaults to on. If someone runs the server with no
configuration at all, it is read-only and verifies the device it connects to. Safe
by default, dangerous only on request.

**Two helper methods:**

```python
def ssh_options(self) -> str: ...
def device_is_allowed(self, device: str) -> bool: ...
```

The first builds the SSH options string. The second implements the device
allow-list: an empty list means "every device in the testbed", a populated one means
"only these".

---

## 3. Guardrails: `validation.py`

This is the file that keeps a language model from doing damage.

### Why validation is necessary

The command strings arriving at the server are produced by a model, and a model can
be influenced by the text it has read — including text that came back from a device.
An interface description is attacker-controllable. So every string is treated as
untrusted input.

### Allow-list, not deny-list, for reads

```python
if head.split()[0].lower() not in {"show", "sh"}:
    raise CommandNotAllowedError(...)
```

The command must **start with** `show`. It is not enough to check that it does not
look dangerous — you cannot enumerate everything that is dangerous, but you can
enumerate what is safe.

### Blocking command smuggling

```python
_COMMAND_SEPARATORS = re.compile(r"[;&\r\n`$<>]")
```

Without this, `show version; reload` would pass a naive "starts with show" check.
Rejecting separators means one request can only ever be one command.

### Restricting the pipe

IOS lets you pipe `show` output into modifiers. Most only filter text, but
`redirect`, `tee` and `append` **write files onto the device**. So only the filters
are allowed:

```python
ALLOWED_PIPE_MODIFIERS = frozenset({"begin", "count", "exclude", "include", "section"})
```

### Deny-list for writes

Configuration is more open-ended than `show`, so here a deny-list catches the
commands that take a device out of service or tamper with access:

```python
(re.compile(r"^\s*reload\b", re.I), "reloading the device"),
(re.compile(r"^\s*write\s+erase\b", re.I), "erasing the startup configuration"),
(re.compile(r"^\s*(no\s+)?username\b", re.I), "managing local user accounts"),
```

Each entry carries a human-readable reason, so the refusal message explains itself.

> This is a safety net, not an authorisation system. Real authorisation belongs on
> the device, in AAA.

### Bounding the output

```python
def truncate(output: str, limit: int) -> str: ...
```

`show tech-support` can be enormous. Truncation stops one command from exhausting
the model's context window.

---

## 4. Connections: `devices.py`

### Loading the testbed

```python
from pyats.topology import loader
return loader.load(str(path))
```

The import sits **inside** the function rather than at the top of the file. That
keeps pyATS out of the import path for the unit tests, so the guardrail tests run in
CI without installing a heavy dependency.

### A context manager for connections

```python
@contextmanager
def connected_device(settings, device_name):
    ...
    device.connect(log_stdout=False, learn_hostname=True)
    try:
        yield device
    finally:
        device.disconnect()
```

**What a context manager is.** It lets calling code write:

```python
with connected_device(settings, "iosv-0") as dev:
    output = dev.execute("show version")
```

Everything before `yield` is setup; everything in the `finally` block is cleanup
that runs **even if the command raises an exception**. Without this pattern, a failed
command leaves a VTY session open on the device, and eventually the device refuses
new logins.

**Why `log_stdout=False`.** Unicon would otherwise echo the session to stdout — the
channel MCP uses for its protocol. That would corrupt the connection to VS Code.

---

## 5. The tools: `server.py`

### Creating the server

```python
mcp = FastMCP("cisco-pyats-mcp")
```

`FastMCP` turns ordinary Python functions into MCP tools.

### Defining a tool

```python
@mcp.tool()
def run_show_command(device: str, command: str) -> str:
    """Run a single read-only `show` command on a device and return its output."""
    settings = _settings()
    safe_command = validate_show_command(command)
    with connected_device(settings, device) as dev:
        output = dev.execute(safe_command, timeout=settings.command_timeout)
    return truncate(output, settings.max_output_chars)
```

Four things to notice:

1. **The decorator** `@mcp.tool()` registers the function as callable by the
   assistant.
2. **The docstring is part of the interface.** It is sent to the model, and it is how
   the model decides which tool fits the user's request. A vague docstring produces
   the wrong tool call.
3. **Type hints matter.** `device: str, command: str` become the tool's input schema.
4. **Validation happens before the connection.** A bad command is rejected without
   ever touching the device.

### Gating the dangerous tool

```python
if not settings.allow_config:
    raise CommandNotAllowedError(
        "Configuration changes are disabled. Set PYATS_MCP_ALLOW_CONFIG=true to enable them."
    )
```

`apply_config` refuses to run at all unless it was explicitly enabled, and saving to
startup-config needs a second, separate switch. Two deliberate actions are required
before anything becomes permanent.

### Logging to stderr

```python
logging.basicConfig(stream=sys.stderr, level=logging.INFO, ...)
```

Never `print()` in an MCP stdio server. Stdout belongs to the protocol; diagnostics
go to stderr.

---

## 6. Practices worth copying

| Practice | Why it helps |
|---|---|
| Validate input at the boundary | One place to audit, one place to test |
| Fail safe by default | A misconfigured deployment is read-only, not destructive |
| Context managers for resources | Cleanup happens even when something raises |
| Configuration from the environment | Same code in a lab, in CI and under an MCP client |
| Small modules with one job each | Each piece is testable on its own |
| Docstrings as the model's interface | Clear descriptions produce correct tool selection |

---

## 7. Adding your own tool

To add a read-only BGP check:

```python
@mcp.tool()
def check_bgp_neighbors(device: str) -> str:
    """Return BGP neighbour state for a device, to confirm sessions are established."""
    settings = _settings()
    with connected_device(settings, device) as dev:
        output = dev.execute("show ip bgp summary", timeout=settings.command_timeout)
    return truncate(output, settings.max_output_chars)
```

Then add a test. The rules every new tool must follow are listed in
[CONTRIBUTING.md](../CONTRIBUTING.md#adding-a-new-mcp-tool).

---

## 8. Takeaway

The networking part of this project is small. The valuable part is the discipline
around it: validate untrusted input, default to safe, always clean up, and keep
configuration out of code. Those habits transfer to every automation script you will
write.
