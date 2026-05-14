#!/usr/bin/env python3
"""Codex PostToolUse adapter for Alpha Insights."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[2]
HOOK_DIR = SKILL_ROOT / "scripts" / "harness" / "hooks"
STAGE_GATE_HOOK = HOOK_DIR / "stage_gate_hook.py"
PROGRESS_LOGGER = HOOK_DIR / "progress_logger.py"


def _tool_input(data: dict[str, Any]) -> Any:
    return data.get("tool_input") or data.get("toolInput") or data.get("input") or {}


def _tool_name(data: dict[str, Any]) -> str:
    return str(data.get("tool_name") or data.get("toolName") or data.get("tool") or "")


def _string_payload(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _extract_paths(data: dict[str, Any]) -> list[str]:
    tool_input = _tool_input(data)
    paths: list[str] = []

    if isinstance(tool_input, dict):
        for key in ("file_path", "path", "target_file", "targetPath"):
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                paths.append(value)
        patch_text = "\n".join(
            _string_payload(tool_input.get(key, ""))
            for key in ("patch", "input", "cmd", "command")
        )
    else:
        patch_text = _string_payload(tool_input)

    for match in re.finditer(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", patch_text, re.MULTILINE):
        paths.append(match.group(1).strip())

    seen: set[str] = set()
    deduped: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            deduped.append(path)
    return deduped


def _normalized_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data)
    payload["tool_name"] = _tool_name(data)
    payload["tool_input"] = _tool_input(data)
    return payload


def _run_hook(script: Path, payload: dict[str, Any]) -> str:
    proc = subprocess.run(
        ["python3", str(script)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout.strip()


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return

    _run_hook(PROGRESS_LOGGER, _normalized_payload(data))

    messages: list[str] = []
    for path in _extract_paths(data):
        payload = dict(data)
        payload["tool_name"] = _tool_name(data) or "ApplyPatch"
        payload["tool_input"] = {"file_path": path}
        output = _run_hook(STAGE_GATE_HOOK, payload)
        if not output:
            continue
        try:
            decoded = json.loads(output)
        except Exception:
            messages.append(output)
        else:
            message = decoded.get("message")
            if message:
                messages.append(str(message))

    if messages:
        print(json.dumps({"decision": "allow", "message": "\n\n".join(messages)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

