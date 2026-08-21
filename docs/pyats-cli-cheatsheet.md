<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Cisco pyATS CLI commands: practical cheat sheet

A hands-on reference for the Cisco **pyATS** and **Genie** CLI commands used most
often in labs, demos and CI/CD pipelines.

Related: [lab guide](lab-guide.md) · [server code explained](server-code-explained.md) ·
[MCP configuration explained](mcp-config-explained.md)

---

## 1. Install & Verify pyATS

Install pyATS together with the Genie libraries, which is what this repository's
`requirements.txt` does:

```bash
pip install "pyats[library]"
```

```bash
pyats version
```

```bash
pyats info
```

---

## 2. Testbed Management (YAML)

Validate testbed file:
```bash
pyats validate testbed testbed.yaml
```

List devices:
```bash
pyats topology devices testbed.yaml
```

Show device connections:
```bash
pyats topology connections testbed.yaml
```

---

## 3. Device Connection (CLI)

Connect using a job file:
```bash
pyats run job connect_devices.py --testbed-file testbed.yaml
```

Launch interactive shell:
```bash
pyats shell --testbed-file testbed.yaml
```

Inside `pyats shell`:
```python
testbed.devices['iosv-1'].connect()
testbed.devices['iosv-1'].execute('show ip route')
```

---

## 4. Running pyATS Jobs & Tests

Run a job:
```bash
pyats run job job.py
```

Run with a testbed:
```bash
pyats run job job.py --testbed-file testbed.yaml
```

Run a specific testcase:
```bash
pyats run job job.py --testcase PingTest
```

Enable debug logging:
```bash
pyats run job job.py --loglevel debug
```

---

## 5. Genie (pyATS Libraries) CLI Commands

Parse CLI output:
```bash
pyats parse "show version" --testbed-file testbed.yaml --device iosv-1
```

Learn full device state:
```bash
pyats learn all --testbed-file testbed.yaml --device iosv-1
```

Learn specific feature:
```bash
pyats learn interface --testbed-file testbed.yaml --device iosv-1
```

Diff snapshots:
```bash
pyats diff pre_snapshot post_snapshot
```

---

## 6. Health & Validation Examples

Run health check job:
```bash
pyats run job health_check.py --testbed-file testbed.yaml
```

Ping validation:
```bash
pyats parse "ping 8.8.8.8" --testbed-file testbed.yaml --device iosv-1
```

Routing table learning:
```bash
pyats learn routing --testbed-file testbed.yaml --device iosv-1
```

---

## 7. Reporting & Results

Generate HTML report:
```bash
pyats report --runinfo runinfo
```

Open report:
```bash
firefox runinfo/report.html
```

View logs:
```bash
cd runinfo/logs
ls
```

---

## 8. Cleanup & Utilities

Clean old runs:
```bash
pyats clean
```

View previous runs:
```bash
pyats logs view
```

---

## 9. CI/CD Usage (GitLab / Jenkins)

Set testbed path:
```bash
export PYATS_TESTBED_PATH=testbed.yaml
```

Run automation:
```bash
pyats run job job.py
```

Exit codes:
- `0` → PASS  
- `1+` → FAIL (pipeline failure)

---

## 10. Command Summary Table

| Task | Command |
|----|----|
| Validate testbed | `pyats validate testbed` |
| Connect devices | `pyats shell` |
| Parse CLI | `pyats parse` |
| Learn device state | `pyats learn` |
| Run automation | `pyats run job` |
| Compare snapshots | `pyats diff` |
| Generate report | `pyats report` |

---

## 11. Further Reading

- [Cisco pyATS on DevNet](https://developer.cisco.com/pyats/)
- [pyATS documentation](https://developer.cisco.com/docs/pyats/)
- [pyATS on GitHub](https://github.com/CiscoTestAutomation/pyats)

---

**Author:** Ranil Fernando  
**Use Case:** Cisco pyATS | Genie | CML | CI/CD Automation  
**Licence:** Apache-2.0 — see [LICENSE](../LICENSE)
