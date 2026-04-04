#!/usr/bin/env python3
"""
Alpha Insights — Stage Compressor

将已完成的 Stage 产出文件压缩为摘要，减少后续 Stage 的上下文消耗。

压缩策略:
- Stage 1-2（定义阶段）: 激进 — 仅保留关键决策
- Stage 3（计划阶段）: 激进 — 仅保留 Track 列表
- Stage 4（研究阶段）: 中等 — 保留 B 级以上证据摘要
- Stage 5（洞察阶段）: 永不压缩

用法:
    python3 compress_stage.py <workspace> --stage 3
    python3 compress_stage.py <workspace> --all
"""

import json
import os
import re
import sys


def compress_stage1(workspace):
    """压缩 user_brief.md → 保留议题 + 档位 + 关键上下文"""
    path = os.path.join(workspace, "user_brief.md")
    if not os.path.isfile(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    summary_lines = []

    # 提取标题行和关键信息
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            summary_lines.append(stripped)
        elif any(kw in stripped for kw in ["议题", "档位", "Tier", "场景", "角色", "topic", "tier"]):
            summary_lines.append(stripped)

    summary = "\n".join(summary_lines) if summary_lines else lines[0] if lines else ""
    return f"[Stage 1 摘要] {summary}"


def compress_stage2(workspace):
    """压缩 research_definition.md → 保留子问题列表 + 框架选择"""
    path = os.path.join(workspace, "research_definition.md")
    if not os.path.isfile(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    summary_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            summary_lines.append(stripped)
        elif re.match(r"^[-*]\s*(Q\d|子问题|假设|H\d|框架)", stripped):
            summary_lines.append(stripped)

    summary = "\n".join(summary_lines) if summary_lines else lines[0] if lines else ""
    return f"[Stage 2 摘要] {summary}"


def compress_stage3(workspace):
    """压缩 research_plan.md → 保留 Track 列表"""
    path = os.path.join(workspace, "research_plan.md")
    if not os.path.isfile(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    summary_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            summary_lines.append(stripped)
        elif re.search(r"Track [A-G]", stripped):
            summary_lines.append(stripped)
        elif re.match(r"^[-*]\s*H\d", stripped):
            summary_lines.append(stripped)

    summary = "\n".join(summary_lines) if summary_lines else lines[0] if lines else ""
    return f"[Stage 3 摘要] {summary}"


def compress_stage4(workspace):
    """压缩 evidence_base.md → 保留 B 级以上证据摘要"""
    path = os.path.join(workspace, "evidence_base.md")
    if not os.path.isfile(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    summary_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            summary_lines.append(stripped)
        # 保留 A 级和 B 级证据行
        elif re.search(r"[AB]\s*级", stripped):
            summary_lines.append(stripped)
        # 保留表头
        elif stripped.startswith("|") and ("编号" in stripped or "证据" in stripped or "Track" in stripped):
            summary_lines.append(stripped)

    summary = "\n".join(summary_lines) if summary_lines else f"[evidence_base.md: {len(lines)} 行]"
    return f"[Stage 4 摘要 - 仅 A/B 级证据]\n{summary}"


COMPRESSORS = {
    1: compress_stage1,
    2: compress_stage2,
    3: compress_stage3,
    4: compress_stage4,
    # Stage 5: 永不压缩
}


def compress_and_save(workspace, stage_num):
    """压缩指定 Stage 并将摘要写入 _state.json"""
    compressor = COMPRESSORS.get(stage_num)
    if compressor is None:
        return {"stage": stage_num, "status": "SKIP", "reason": "无压缩器或禁止压缩"}

    summary = compressor(workspace)
    if summary is None:
        return {"stage": stage_num, "status": "SKIP", "reason": "源文件不存在"}

    # 写入 _state.json
    state_path = os.path.join(workspace, "_state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            if "stage_summaries" not in state:
                state["stage_summaries"] = {}
            state["stage_summaries"][str(stage_num)] = summary
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, OSError):
            pass  # fail-open: _state.json 损坏时跳过摘要写入，不阻断压缩流程

    # 输出摘要供 AI 直接使用
    token_estimate = len(summary) / 2.0
    return {
        "stage": stage_num,
        "status": "COMPRESSED ✅",
        "summary_tokens": int(token_estimate),
        "summary": summary,
    }


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 compress_stage.py <workspace> --stage N")
        print("  python3 compress_stage.py <workspace> --all")
        sys.exit(1)

    workspace = sys.argv[1]

    if "--all" in sys.argv:
        results = []
        for stage_num in sorted(COMPRESSORS.keys()):
            results.append(compress_and_save(workspace, stage_num))
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        stage_num = None
        for i, arg in enumerate(sys.argv):
            if arg == "--stage" and i + 1 < len(sys.argv):
                stage_num = int(sys.argv[i + 1])
        if stage_num is None:
            print("错误: 需要 --stage N 或 --all")
            sys.exit(1)
        result = compress_and_save(workspace, stage_num)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
