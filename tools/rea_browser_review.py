#!/usr/bin/env python3
"""Bounded REA browser proof; two fixed public pages, no financial imports."""

from __future__ import annotations

import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import threading
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    ("idbourse", "https://www.idbourse.com/"),
    ("tradingview", "https://www.tradingview.com/"),
)


def scenario(browser: str, url: str) -> dict:
    return {
        "browser": {"mode": "launch", "executable_path": browser, "headless": True},
        "start_url": {"url": url, "query": []},
        "environment": {
            "viewport": {"width": 1440, "height": 1000},
            "locale": "fr-FR",
            "timezone": "Africa/Casablanca",
        },
        "actions": [{"step_id": "settle", "action": "wait_for_timeout", "duration_ms": 2500}],
        "capture": {
            "at_end": ["url", "dom", "accessibility", "screenshot"],
            "events": ["network", "page-errors"],
            "network": {"request_body": False, "response_body": False, "header_values": False},
        },
    }


def find_capture(value):
    if isinstance(value, dict):
        if "browser" in value and "steps" in value and "completeness" in value:
            return value
        for key in ("normalized_result", "data", "result", "value"):
            found = find_capture(value.get(key))
            if found is not None:
                return found
    return None


def capture_one(cli: str, browser: str, out: Path, name: str, url: str) -> dict:
    request = out / f"{name}.request.json"
    request.write_text(json.dumps(scenario(browser, url), indent=2), encoding="utf-8")
    stdout = out / f"{name}.evidence.json"
    stderr = out / f"{name}.stderr.txt"
    status = {"target": name, "requested_url": url, "status": "unavailable"}
    with stdout.open("w") as output, stderr.open("w") as errors:
        try:
            result = subprocess.run(
                [cli, "capture-browser-scenario", str(request), "--format", "json", "--full-output"],
                stdout=output, stderr=errors, timeout=80, check=False,
            )
            status["exit_code"] = result.returncode
        except subprocess.TimeoutExpired:
            status["reason"] = "bounded_capture_timeout"
            return status
    status["evidence_sha256"] = hashlib.sha256(stdout.read_bytes()).hexdigest()
    try:
        evidence = json.loads(stdout.read_text())
    except (ValueError, OSError):
        status["reason"] = "no_valid_json_evidence"
        return status
    observed = find_capture(evidence)
    if observed is None:
        status["reason"] = "no_completed_browser_capture"
        return status
    steps = observed["steps"]
    final = steps[-1]
    artifacts = final["artifacts"]
    status.update({
        "browser": observed["browser"],
        "steps": [{"id": s["step_id"], "status": s["status"], "error": s.get("error")} for s in steps],
        "artifacts": {k: v["state"] for k, v in artifacts.items()},
        "final_url": final["after_url"],
        "network_events": observed["events"]["retained"],
        "completeness": observed["completeness"],
        "limitations": observed["limitations"],
    })
    dom = artifacts.get("dom", {}).get("value", {}).get("text", "")
    screenshot = artifacts.get("screenshot", {}).get("value", {})
    status["dom_bytes"] = len(dom.encode())
    status["screenshot_present"] = bool(screenshot)
    good = all(s["status"] == "completed" for s in steps)
    good = good and artifacts.get("dom", {}).get("state") == "captured"
    good = good and artifacts.get("screenshot", {}).get("state") == "captured"
    status["status"] = "captured" if good else "partial"
    # A successful capture of an access wall is not a successful product inspection.
    text = dom.casefold()
    if any(marker in text for marker in ("verify you are human", "just a moment...", "access denied", "site unavailable")):
        status["status"] = "access_limited"
    if name == "nour_local" and "Nour" not in dom:
        status["status"] = "invalid_local_content"
    return status


def main() -> int:
    cli = os.environ["NOUR_REA_CLI"]
    browser = os.environ["NOUR_REA_BROWSER"]
    out = Path(os.environ["NOUR_REA_OUTPUT"])
    out.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output([cli, "--version"], text=True).strip()
    browser_version = subprocess.check_output([browser, "--version"], text=True).strip()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "web"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "rea_version": version,
        "browser_version": browser_version,
        "financial_data_changed": False,
        "captures": [],
        "scope": "Own local Nour page, then two unauthenticated public home pages only; no account or private endpoints.",
    }
    try:
        local = capture_one(cli, browser, out, "nour_local", f"http://127.0.0.1:{server.server_port}/index.html")
        report["captures"].append(local)
        # A broken browser never gets reported as ready or retried on third-party pages.
        if local["status"] == "captured":
            for name, url in TARGETS:
                report["captures"].append(capture_one(cli, browser, out, name, url))
        report["browser_ready"] = local["status"] == "captured"
    finally:
        server.shutdown()
        server.server_close()
        (out / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    compact = [{k: c.get(k) for k in ("target", "status", "reason", "dom_bytes", "screenshot_present")} for c in report["captures"]]
    print(json.dumps({"browser_ready": report["browser_ready"], "rea_version": version, "browser_version": browser_version, "captures": compact}, ensure_ascii=False))
    return 0 if report["browser_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
