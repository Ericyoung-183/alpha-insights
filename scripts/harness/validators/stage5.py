"""Stage 5: Insights 验证器"""

from .common import (
    ValidationResult, file_exists, file_contains_pattern,
    file_contains_keyword, count_pattern, get_tier,
)


def validate(workspace):
    r = ValidationResult(5)
    f = "insights.md"
    tier = get_tier(workspace)

    if not file_exists(workspace, f):
        r.fail(f"{f} 不存在")
        return r
    r.pass_check(f"{f} 存在")

    # 必须含评分
    has_score = file_contains_pattern(workspace, f, r"[0-9]+\s*分|评分|score|Score")
    if has_score:
        r.pass_check("含洞察评分")
    else:
        r.fail("未检测到洞察评分")

    # 红队审查（所有档位必须执行）
    has_red = file_contains_pattern(workspace, f, r"红队|red.?team|\b8a\b|Red Team")
    if has_red:
        r.pass_check("红队审查记录存在")
    else:
        r.fail("未检测到红队审查记录（所有档位必须执行）")

    # 蓝队审查（所有档位必须执行）
    has_blue = file_contains_pattern(workspace, f, r"蓝队|blue.?team|\b8b\b|Blue Team")
    if has_blue:
        r.pass_check("蓝队审查记录存在")
    else:
        r.fail("未检测到蓝队审查记录（所有档位必须执行）")

    # WARN: 红队实质挑战记录
    if has_red:
        has_substantive = file_contains_pattern(
            workspace, f, r"实质|致命|Substantive|Fatal"
        )
        if has_substantive:
            r.pass_check("红队含实质/致命级挑战记录")
        else:
            r.warn("红队审查未检测到实质/致命级挑战 — 每个核心洞察至少 1 个实质挑战")

    # WARN: 洞察数量
    insight_count = count_pattern(workspace, f, r"(?:洞察|Insight)\s*[I#]?\s*\d")
    if insight_count < 3:
        r.warn(f"仅检测到 {insight_count} 个洞察（建议 ≥ 3）")

    # WARN: 用户确认状态
    has_confirm = file_contains_pattern(
        workspace, f, r"用户确认|已确认|待确认|已修改"
    )
    if has_confirm:
        r.pass_check("含用户确认状态记录")
    else:
        r.warn("未检测到用户确认状态 — insights.md 应记录洞察确认结果")

    # WARN: 关键变量监测
    has_key_var = (
        file_contains_keyword(workspace, f, "关键变量")
        or file_contains_keyword(workspace, f, "监测清单")
    )
    if has_key_var:
        r.pass_check("含关键变量/监测清单")
    else:
        r.warn("未检测到关键变量监测清单")

    # WARN: So What 链深度（检测层级标记：→/⇒/层/layer 或 So What 出现次数）
    so_what_count = count_pattern(workspace, f, r"So What|so what|So what")
    layer_markers = count_pattern(workspace, f, r"→.*→|⇒.*⇒|第[一二三四1-4]层|Layer [1-4]|现象[\s\S]*?含义[\s\S]*?策略|含义[\s\S]*?策略[\s\S]*?行动")
    depth_signal = max(so_what_count, layer_markers)
    if depth_signal >= 3:
        r.pass_check(f"So What 链深度信号: {depth_signal}（So What {so_what_count} 处 + 层级标记 {layer_markers} 处）")
    else:
        r.warn(f"So What 链深度不足（So What {so_what_count} 处 + 层级标记 {layer_markers} 处，要求核心洞察 ≥3 层推导）")

    # WARN: Pre-mortem 风险记录
    has_premortem = (
        file_contains_keyword(workspace, f, "Pre-mortem")
        or file_contains_keyword(workspace, f, "pre-mortem")
        or file_contains_keyword(workspace, f, "风险提示")
        or file_contains_keyword(workspace, f, "失败原因")
    )
    if has_premortem:
        r.pass_check("含 Pre-mortem 风险记录")
    else:
        r.warn("未检测到 Pre-mortem 风险记录")

    # WARN: SMART 测试记录（匹配完整词 SMART，或全拼 Specific/Measurable...，或展开格式 **S**: / **M**: ...）
    has_smart = (
        file_contains_keyword(workspace, f, "SMART")
        or file_contains_pattern(workspace, f, r"Specific|Measurable|Achievable|Relevant|Time.?bound")
        or file_contains_pattern(workspace, f, r"\*{0,2}[SMART]\*{0,2}\s*[:：]")
    )
    if has_smart:
        r.pass_check("含 SMART 测试记录")
    else:
        r.warn("未检测到 SMART 测试记录")

    # 行动建议
    has_action = file_contains_keyword(workspace, f, "建议") or file_contains_keyword(workspace, f, "行动")
    if has_action:
        r.pass_check("含行动建议")
    else:
        r.warn("未检测到行动建议")

    return r
