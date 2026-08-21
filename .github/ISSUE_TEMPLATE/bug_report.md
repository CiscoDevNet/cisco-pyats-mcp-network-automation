---
name: Bug report
about: Report a problem with the MCP server, the tools, or the documentation
title: "[Bug] "
labels: bug
---

## Description

A clear description of what went wrong.

## Steps to reproduce

1. ...
2. ...
3. ...

## Expected behaviour

What you expected to happen.

## Actual behaviour / error output

```text
Paste the error here. Redact IP addresses, hostnames and credentials.
```

## Environment

- OS and version:
- Python version (`python --version`):
- pyATS version (`pyats version`):
- MCP client (VS Code + Copilot Chat, other):
- Device platform (IOSv on CML, IOS XE, other):

## Configuration

- `PYATS_MCP_ALLOW_CONFIG`:
- `PYATS_MCP_ALLOWED_DEVICES`:
- `PYATS_MCP_INSECURE_SSH`:

## Pre-flight check output

Output of `python scripts/check_env.py`:

```text

```

## Checklist

- [ ] I have removed all credentials, real IP addresses and hostnames from this report.
- [ ] `python scripts/check_env.py` completes successfully.
- [ ] `python scripts/run_show.py --device <name> --command "show version"` works.
