#!/usr/bin/env python3
"""Hook 3: PreToolUse on Write — block direct .html/.htm file writes.

Stage 6 requires HTML generation via Bash+Python because:
- Model output layer randomly filters ECharts 'data' keywords
- Write tool truncates large HTML files in tight context
"""

import json
import sys


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        # malformed input → allow but warn (transparent failure)
        json.dump({
            "decision": "allow",
            "message": "⚠️ html_write_guard: failed to parse input, allowing by default",
        }, sys.stdout, ensure_ascii=False)
        return

    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""

    if file_path.lower().endswith((".html", ".htm")):
        json.dump({
            "decision": "block",
            "reason": (
                "HTML 文件必须通过 Bash + Python 脚本生成（report_helper.py 或手动 dk 拼接）。"
                "Write 工具被禁止写 .html，因为模型输出层会随机过滤 ECharts 的 data 关键字，"
                "且 Write 在 context 紧张时会截断大文件。请参照 Stage 6 指令。"
            ),
        }, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
