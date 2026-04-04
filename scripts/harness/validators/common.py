"""共享验证工具函数"""

import json
import os
import re


def get_tier(workspace):
    """从 _state.json 读取研究档位（Tier 1/2/3），默认 Tier 3"""
    path = os.path.join(workspace, "_state.json")
    if not os.path.isfile(path):
        return 3
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            state = json.load(f)
        return int(state.get("tier", 3))
    except (json.JSONDecodeError, ValueError, TypeError):
        return 3


def file_exists(workspace, filename):
    return os.path.isfile(os.path.join(workspace, filename))


def file_line_count(workspace, filename):
    path = os.path.join(workspace, filename)
    if not os.path.isfile(path):
        return 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def file_size_bytes(workspace, filename):
    path = os.path.join(workspace, filename)
    if not os.path.isfile(path):
        return 0
    return os.path.getsize(path)


def file_contains_keyword(workspace, filename, keyword):
    path = os.path.join(workspace, filename)
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return keyword in content


def file_contains_pattern(workspace, filename, pattern):
    path = os.path.join(workspace, filename)
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return bool(re.search(pattern, content, re.MULTILINE))


def count_pattern(workspace, filename, pattern):
    path = os.path.join(workspace, filename)
    if not os.path.isfile(path):
        return 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return len(re.findall(pattern, content, re.MULTILINE))


def check_anti_patterns(workspace, filename):
    """检测报告中的反模式用语"""
    anti_patterns = ["全面分析", "综合考虑", "需要进一步研究", "有待观察", "不一而足"]
    warnings = []
    for ap in anti_patterns:
        count = count_pattern(workspace, filename, re.escape(ap))
        if count > 0:
            warnings.append(f"反模式「{ap}」出现 {count} 次")
    return warnings


class ValidationResult:
    """验证结果收集器"""

    def __init__(self, stage):
        self.stage = stage
        self.checks = []
        self.warnings = []
        self.failed = False

    def fail(self, message):
        self.checks.append({"level": "FAIL", "message": message})
        self.failed = True

    def pass_check(self, message):
        self.checks.append({"level": "PASS", "message": message})

    def warn(self, message):
        self.warnings.append(message)

    def to_dict(self):
        return {
            "stage": self.stage,
            "gate": "BLOCKED ❌" if self.failed else "PASS ✅",
            "checks": self.checks,
            "warnings": self.warnings,
        }
