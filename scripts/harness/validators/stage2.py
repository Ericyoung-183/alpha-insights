"""Stage 2: Framing 验证器"""

from .common import ValidationResult, file_exists, file_contains_keyword, count_pattern


def validate(workspace):
    r = ValidationResult(2)
    f = "research_definition.md"

    if not file_exists(workspace, f):
        r.fail(f"{f} 不存在")
        return r
    r.pass_check(f"{f} 存在")

    # 必须含子问题
    has_subq = (
        file_contains_keyword(workspace, f, "子问题")
        or file_contains_keyword(workspace, f, "sub-question")
        or file_contains_keyword(workspace, f, "Q1")
    )
    if has_subq:
        r.pass_check("含子问题")
    else:
        r.fail("未检测到子问题")

    # 必须含透镜分配
    has_lens = (
        file_contains_keyword(workspace, f, "透镜")
        or file_contains_keyword(workspace, f, "lens")
        or file_contains_keyword(workspace, f, "分析透镜")
    )
    if has_lens:
        r.pass_check("含透镜分配")
    else:
        r.fail("未检测到透镜分配（分析透镜 / lens）")

    # WARN: 框架数量
    framework_count = count_pattern(workspace, f, r"(?:框架|framework|模型|model)")
    if framework_count < 2:
        r.warn(f"框架/模型提及仅 {framework_count} 次，建议至少 2 个框架")

    # WARN: IQR 复核标记
    has_iqr = file_contains_keyword(workspace, f, "IQR") or file_contains_keyword(workspace, f, "独立质量复核")
    if has_iqr:
        r.pass_check("IQR 复核已执行")
    else:
        r.warn("未检测到 IQR 复核标记（建议执行独立质量复核）")

    return r
