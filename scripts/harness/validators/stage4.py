"""Stage 4: Research 验证器"""

from .common import (
    ValidationResult, file_exists, file_line_count,
    file_contains_keyword, file_contains_pattern, count_pattern,
    get_tier, load_state,
)


def validate(workspace):
    r = ValidationResult(4)
    f = "evidence_base.md"
    tier = get_tier(workspace)

    if not file_exists(workspace, f):
        r.fail(f"{f} 不存在")
        return r
    r.pass_check(f"{f} 存在")

    # 行数按 Tier 区分（Tier 1 ≥ 10 / Tier 2 ≥ 20 / Tier 3 ≥ 40）
    min_lines = {1: 10, 2: 20, 3: 40}.get(tier, 10)
    lines = file_line_count(workspace, f)
    if lines < min_lines:
        r.fail(f"仅 {lines} 行（Tier {tier} 要求 ≥ {min_lines}）")
    else:
        r.pass_check(f"行数: {lines}（Tier {tier} 要求 ≥ {min_lines}）")

    # 置信度标注
    has_confidence = file_contains_pattern(workspace, f, r"[A-D]\s*级|置信度|confidence")
    if has_confidence:
        r.pass_check("含置信度标注")
    else:
        r.warn("未检测到置信度标注")

    # 证据条目格式
    evidence_count = count_pattern(workspace, f, r"^\| [A-Z][0-9]+-[0-9]+")
    if evidence_count > 0:
        r.pass_check(f"标准格式证据条目: {evidence_count} 条")
    else:
        r.warn("未找到标准格式证据条目（A1-01 格式）")

    # Track 标识
    has_track = file_contains_pattern(workspace, f, r"Track [A-G]")
    if has_track:
        r.pass_check("含 Track 标识")
    else:
        r.warn("未检测到 Track 标识")

    # FAIL: 核心数据至少 1 条 ≥B 级
    high_quality = count_pattern(workspace, f, r"[AB]\s*级")
    if high_quality == 0:
        r.fail("未检测到 A/B 级证据（门控要求：核心数据至少 1 条 ≥B 级）")
    else:
        r.pass_check(f"A/B 级证据: {high_quality} 条")

    # WARN: B 级以上占比
    total_evidence = count_pattern(workspace, f, r"[A-D]\s*级")
    if total_evidence > 0:
        ratio = high_quality / total_evidence
        if ratio < 0.5:
            r.warn(f"B 级以上证据占比 {ratio:.0%}（建议 ≥ 50%）")

    # 加载 _state.json（一次加载，多处使用）
    state = load_state(workspace)

    # 访谈催收检查点验证
    if state and state.get("interview_activated"):
        if state.get("interview_checkpoint_done"):
            result = state.get("interview_checkpoint_result", "unknown")
            r.pass_check(f"访谈催收检查点已执行（结果: {result}）")
        else:
            r.warn("Stage 3.5 已激活访谈，但未执行催收检查点 — 请在生成 evidence_base 前询问用户访谈进展")

    # WARN: 框架分析结论
    has_framework = (
        file_contains_keyword(workspace, f, "框架")
        or file_contains_keyword(workspace, f, "PESTEL")
        or file_contains_keyword(workspace, f, "Porter")
        or file_contains_keyword(workspace, f, "SWOT")
        or file_contains_pattern(workspace, f, r"框架[\s\S]*?结论|框架[\s\S]*?分析")
    )
    if has_framework:
        r.pass_check("含框架分析记录")
    else:
        r.warn("未检测到框架分析结论 — Stage 4 要求框架分析结论独立产出")

    # WARN: IQR 复核（从 _state.json 读取，不从 deliverable 文件搜索）
    if state and state.get("iqr_results"):
        iqr_data = state["iqr_results"].get("4")
        if iqr_data:
            result = iqr_data.get("result", "unknown")
            if result == "BLOCK":
                r.fail("IQR 复核阻断（BLOCK）— 需修复后重新提交")
            elif result in ("PASS", "REVISE"):
                r.pass_check(f"IQR 复核已执行（{result}）")
            else:
                r.warn(f"IQR 复核结果异常: {result}")
        else:
            r.warn("未检测到 Stage 4 IQR 复核记录（建议执行独立质量复核）")
    else:
        r.warn("未检测到 IQR 复核记录（建议执行独立质量复核）")

    return r
