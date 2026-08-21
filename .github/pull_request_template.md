## Description

What does this pull request change, and why?

Fixes #

## Type of change

- [ ] Bug fix
- [ ] New MCP tool or feature
- [ ] Documentation
- [ ] Build, CI or tooling

## How this was tested

- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `pytest`
- [ ] `bandit -r mcp_server scripts`
- [ ] Tested against a live device (state platform and image):

## Checklist

- [ ] No credentials, real IP addresses, hostnames or testbed files are included.
- [ ] New caller-supplied input is validated in `mcp_server/validation.py`.
- [ ] Anything that changes device state is gated behind an environment variable.
- [ ] No `print()` to stdout was added to the server (stdout carries MCP frames).
- [ ] Tests were added or updated.
- [ ] README and CHANGELOG were updated where behaviour changed.
