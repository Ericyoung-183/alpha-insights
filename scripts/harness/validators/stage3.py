"""Stage 3: Planning 验证器"""

from .common import (
    ValidationResult, file_exists, count_pattern,
    file_contains_keyword, file_contains_pattern,
)


def validate(workspace):
    r = ValidationResult(3)
    f = "research_plan.md"

    if not file_exists(workspace, f):
        r.fail(f"{f} 不存在")
        return r
    r.pass_check(f"{f} 存在")

    # WARN: Track 数量
    track_count = count_pattern(workspace, f, r"Track [A-G]")
    if track_count < 3:
        r.warn(f"仅检测到 {track_count} 个 Track（建议 ≥ 3）")
    else:
        r.pass_check(f"Track 数量: {track_count}")

    # WARN: 假设确认记录（Q→H→Lens 映射）
    has_hypothesis = (
        file_contains_pattern(workspace, f, r"H[0-9]")
        or file_contains_keyword(workspace, f, "假设")
    )
    if has_hypothesis:
        r.pass_check("含假设记录")
    else:
        r.warn("未检测到假设记录（H1/H2... 或 '假设' 关键词）")

    # FAIL: 访谈决策记录（⛔ 决策环节不可跳过，用户可选择不做访谈）
    has_interview_decision = (
        file_contains_keyword(workspace, f, "访谈")
        or file_contains_keyword(workspace, f, "interview")
    )
    if has_interview_decision:
        r.pass_check("含访谈决策记录")
    else:
        r.fail("未检测到访谈决策记录 — 必须向用户提出访谈建议并记录决策（用户可选择不做，但决策环节不可跳过）")

    return r
