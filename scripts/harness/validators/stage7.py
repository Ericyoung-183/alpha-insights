"""Stage 7: Iteration & Closure 验证器

Stage 7 无门控出口（终态），所有检查均为 advisory（WARN），不阻断。
"""

from .common import ValidationResult, file_exists, file_size_bytes


def validate(workspace):
    r = ValidationResult(7)

    # report.html 应该存在（Stage 6 产物）
    if not file_exists(workspace, "report.html"):
        r.warn("report.html 不存在 — Stage 6 可能未完成")
        return r
    r.pass_check("report.html 存在")

    # insights.md 必须存在（Stage 5 产物）
    if not file_exists(workspace, "insights.md"):
        r.warn("insights.md 缺失 — 迭代时可能缺少洞察上下文")
    else:
        r.pass_check("insights.md 存在")

    # evidence_base.md 必须存在（Stage 4 产物）
    if not file_exists(workspace, "evidence_base.md"):
        r.warn("evidence_base.md 缺失 — 迭代时可能缺少证据上下文")
    else:
        r.pass_check("evidence_base.md 存在")

    # report.html 大小合理（迭代后不应变小）
    size = file_size_bytes(workspace, "report.html")
    if size < 5000:
        r.warn(f"report.html 仅 {size} 字节，可能迭代后内容不完整")
    else:
        r.pass_check(f"report.html 大小: {size} 字节")

    return r
