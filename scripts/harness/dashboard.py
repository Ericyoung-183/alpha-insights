#!/usr/bin/env python3
"""
Alpha Insights — Review Dashboard

在 Stage 5 → Stage 6 转场前，汇总展示研究质量全景。
读取 _state.json + 各阶段交付物，提取关键质量指标。

用法:
    python3 scripts/harness/dashboard.py <workspace_path>

输出:
    格式化的质量总览文本（非 JSON），可直接展示给用户。
"""

import json
import os
import re
import sys


def _load_state(workspace):
    path = os.path.join(workspace, "_state.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _read_file(workspace, filename):
    path = os.path.join(workspace, filename)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _file_exists(workspace, filename):
    return os.path.isfile(os.path.join(workspace, filename))


def _file_size(workspace, filename):
    path = os.path.join(workspace, filename)
    if not os.path.isfile(path):
        return 0
    return os.path.getsize(path)


# ── Stage 2: Research Definition ──

def assess_stage2(workspace):
    content = _read_file(workspace, "research_definition.md")
    if content is None:
        return "❌ 未找到", []

    details = []
    # 子问题计数
    q_count = len(re.findall(r"(?:^|\n)\s*(?:Q\d|子问题|Sub-question)", content, re.IGNORECASE))
    if q_count == 0:
        q_count = len(re.findall(r"(?:^|\n)\s*\d+\.\s", content))
    details.append(f"子问题 {q_count} 个")

    # MECE 检测
    if "MECE" in content or "mece" in content.lower():
        details.append("MECE ✓")

    # 框架计数
    fw_matches = re.findall(r"(?:框架|framework|模型|model)[：:]\s*(\S+)", content, re.IGNORECASE)
    fw_count = len(fw_matches)
    if fw_count > 0:
        details.append(f"框架: {' + '.join(fw_matches[:3])}")
    else:
        # 尝试从 state 中获取
        state = _load_state(workspace)
        if state and state.get("frameworks_loaded"):
            fw_names = state["frameworks_loaded"]
            details.append(f"框架: {' + '.join(fw_names[:3])}")

    return "✅ 已产出", details


# ── Stage 3: Research Plan ──

def assess_stage3(workspace):
    content = _read_file(workspace, "research_plan.md")
    if content is None:
        return "❌ 未找到", []

    details = []
    # 假设计数
    h_count = len(re.findall(r"(?:^|\n)\s*H\d", content))
    if h_count == 0:
        h_count = len(re.findall(r"假设", content))
    details.append(f"假设 {h_count} 个")

    # Q→H 映射
    qh_map = re.findall(r"→\s*Q\d|Q\d.*→|对应.*Q\d", content)
    if qh_map:
        details.append("Q→H 映射 ✓")

    # 数据源类别数
    ds_count = len(re.findall(r"Track\s+[A-G]", content))
    if ds_count > 0:
        details.append(f"数据轨道 {ds_count} 类")

    return "✅ 已产出", details


# ── Stage 4: Evidence Base ──

def assess_stage4(workspace):
    content = _read_file(workspace, "evidence_base.md")
    if content is None:
        return "❌ 未找到", []

    details = []
    lines = content.strip().split("\n")
    details.append(f"证据 {len(lines)} 行")

    # 置信度分布
    a_count = len(re.findall(r"\bA\s*级|置信度.*A|confidence.*A", content, re.IGNORECASE))
    b_count = len(re.findall(r"\bB\s*级|置信度.*B|confidence.*B", content, re.IGNORECASE))
    c_count = len(re.findall(r"\bC\s*级|置信度.*C|confidence.*C", content, re.IGNORECASE))
    total = a_count + b_count + c_count
    if total > 0:
        a_pct = round(a_count / total * 100)
        b_pct = round(b_count / total * 100)
        c_pct = round(c_count / total * 100)
        details.append(f"A 级 {a_pct}% · B 级 {b_pct}% · C 级 {c_pct}%")
        if (a_count + b_count) / total < 0.5:
            details.append("⚠️ B 级以上占比 < 50%")

    return "✅ 已产出", details


# ── Stage 5: Insights ──

def assess_stage5(workspace):
    content = _read_file(workspace, "insights.md")
    if content is None:
        return "❌ 未找到", []

    details = []
    # 洞察计数（寻找评分标记）
    scores = re.findall(r"(\d{1,2})\s*[/／]\s*20|评分[：:]\s*(\d{1,2})|=\s*(\d{1,2})\s*分", content)
    score_values = [int(s[0] or s[1] or s[2]) for s in scores if (s[0] or s[1] or s[2])]

    if score_values:
        core = [s for s in score_values if s >= 18]
        secondary = [s for s in score_values if 16 <= s < 18]
        details.append(f"洞察 {len(score_values)} 个")
        if core:
            details.append(f"核心洞察 A 类 {len(core)} 个（18-20 分）")
        if secondary:
            details.append(f"核心洞察 B 类 {len(secondary)} 个（16-17 分）")
    else:
        details.append("⚠️ 未检测到评分")

    # 红蓝队标记
    has_red = bool(re.search(r"红队|red.?team", content, re.IGNORECASE))
    has_blue = bool(re.search(r"蓝队|blue.?team", content, re.IGNORECASE))
    if has_red and has_blue:
        # 检查致命挑战
        fatal = re.findall(r"致命", content)
        if fatal:
            details.append(f"红队: {len(fatal)} 致命挑战已处理")
        else:
            details.append("红蓝队审查 ✓")
    elif has_red:
        details.append("红队审查 ✓ | ⚠️ 蓝队缺失")
    elif has_blue:
        details.append("⚠️ 红队缺失 | 蓝队审查 ✓")

    return "✅ 已产出", details


# ── Overall Assessment ──

def overall_assessment(stages):
    """根据各阶段状态给出总体评估"""
    failed = [name for name, (status, _) in stages.items() if "❌" in status]
    warnings = []
    for name, (_, details) in stages.items():
        for d in details:
            if "⚠️" in d:
                warnings.append(f"{name}: {d}")

    if failed:
        return f"❌ {len(failed)} 个阶段未通过门控（{', '.join(failed)}），需修复后再进入 Stage 6"
    elif warnings:
        return f"⚠️ 整体通过，{len(warnings)} 项警告建议关注"
    else:
        return "✅ 全部通过，可进入 Stage 6 报告生成"


def generate_dashboard(workspace):
    """生成研究质量总览"""
    stages = {
        "研究定义 (S2)": assess_stage2(workspace),
        "研究计划 (S3)": assess_stage3(workspace),
        "证据基础 (S4)": assess_stage4(workspace),
        "洞察生成 (S5)": assess_stage5(workspace),
    }

    # 读取 Tier 信息
    state = _load_state(workspace)
    tier_str = f"Tier {state['tier']}" if state and "tier" in state else "未知"

    lines = []
    lines.append("━━━ 研究质量总览 ━━━")
    lines.append(f"📊 研究档位: {tier_str}")
    lines.append("")

    for name, (status, details) in stages.items():
        detail_str = " | ".join(details) if details else "无详情"
        lines.append(f"📋 {name}   {status} | {detail_str}")

    lines.append("")
    lines.append(f"⚡ 总体评估: {overall_assessment(stages)}")
    lines.append("━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 dashboard.py <workspace_path>")
        sys.exit(1)

    workspace = sys.argv[1]
    if not os.path.isdir(workspace):
        print(f"错误: workspace 目录不存在: {workspace}")
        sys.exit(1)

    print(generate_dashboard(workspace))


if __name__ == "__main__":
    main()
