"""Stage 6: Report 验证器"""

from .common import (
    ValidationResult, file_exists, file_size_bytes,
    file_contains_keyword, count_pattern, check_anti_patterns,
    get_tier,
)


def validate(workspace):
    r = ValidationResult(6)
    f = "report.html"
    tier = get_tier(workspace)

    if not file_exists(workspace, f):
        r.fail(f"{f} 不存在")
        return r
    r.pass_check(f"{f} 存在")

    # 文件大小（< 5KB 几乎不可能是完整报告）
    size = file_size_bytes(workspace, f)
    if size < 5000:
        r.fail(f"文件仅 {size} 字节（要求 ≥ 5KB），报告不完整")
    else:
        r.pass_check(f"文件大小: {size} 字节")

    # 页面结构（章节页是 FAIL，其余是 WARN）
    if file_contains_keyword(workspace, f, "chapter-section"):
        r.pass_check("章节页存在")
    else:
        r.fail("章节页缺失（chapter-section）— 报告无正文内容")

    for section_id, label in [
        ("cover-page", "封面页"),
        ("toc-page", "目录页"),
        ("footer-page", "尾页"),
    ]:
        if file_contains_keyword(workspace, f, section_id):
            r.pass_check(f"{label}存在")
        else:
            r.fail(f"{label}缺失（{section_id}）— 完整报告必须包含封面、目录和尾页")

    # ECharts
    if file_contains_keyword(workspace, f, "echarts"):
        r.pass_check("ECharts 引用存在")
    else:
        r.warn("ECharts 引用缺失")

    if file_contains_keyword(workspace, f, "echarts.init"):
        r.pass_check("ECharts 初始化代码存在")
    else:
        r.warn("ECharts 初始化代码缺失")

    # data 键完整性
    data_count = (
        count_pattern(workspace, f, r'"data"')
        + count_pattern(workspace, f, r'\bdata\s*:')
    )
    if data_count > 0:
        r.pass_check(f"ECharts data 键存在（{data_count} 处）")
    else:
        r.warn("ECharts data 键为 0 — 可能被模型输出过滤！")

    # 图表数量（Tier 2 ≥3，Tier 3 ≥6，Tier 1 建议但非必须）
    chart_count = count_pattern(workspace, f, r"echarts\.init")
    if tier >= 3 and chart_count < 6:
        r.fail(f"ECharts 图表仅 {chart_count} 个（Tier 3 要求 ≥6）")
    elif tier >= 2 and chart_count < 3:
        r.fail(f"ECharts 图表仅 {chart_count} 个（Tier 2 要求 ≥3）")
    elif chart_count >= 3:
        r.pass_check(f"ECharts 图表 {chart_count} 个")
    elif chart_count > 0:
        r.warn(f"ECharts 图表仅 {chart_count} 个")
    else:
        r.warn("无 ECharts 图表")

    # 反模式检测
    ap_warnings = check_anti_patterns(workspace, f)
    for w in ap_warnings:
        r.warn(w)

    # WARN: IQR 复核标记
    has_iqr = (
        file_contains_keyword(workspace, f, "IQR")
        or file_contains_keyword(workspace, f, "独立质量复核")
    )
    if has_iqr:
        r.pass_check("IQR 复核已执行")
    else:
        r.warn("未检测到 IQR 复核标记（建议执行独立质量复核）")

    return r
