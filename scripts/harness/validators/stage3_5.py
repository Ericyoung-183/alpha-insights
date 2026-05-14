"""Stage 3.5: Interview Prep 验证器"""

from .common import (
    ValidationResult, file_exists, file_contains_keyword,
    file_contains_pattern, count_pattern,
)


def validate(workspace):
    r = ValidationResult(3.5)
    f = "interview_guides.md"

    if not file_exists(workspace, f):
        r.fail(f"{f} 不存在")
        return r
    r.pass_check(f"{f} 存在")

    has_profile = (
        file_contains_keyword(workspace, f, "访谈对象")
        or file_contains_keyword(workspace, f, "对象画像")
        or file_contains_keyword(workspace, f, "interviewee")
        or file_contains_keyword(workspace, f, "target role")
    )
    if has_profile:
        r.pass_check("含访谈对象画像")
    else:
        r.fail("未检测到访谈对象画像")

    has_goal = (
        file_contains_keyword(workspace, f, "访谈目标")
        or file_contains_keyword(workspace, f, "验证假设")
        or file_contains_keyword(workspace, f, "objective")
        or file_contains_keyword(workspace, f, "hypothesis")
    )
    if has_goal:
        r.pass_check("含访谈目标/假设映射")
    else:
        r.fail("未检测到访谈目标或假设映射")

    has_questions = (
        file_contains_keyword(workspace, f, "问题提纲")
        or file_contains_keyword(workspace, f, "核心问题")
        or file_contains_keyword(workspace, f, "questions")
    )
    if has_questions:
        r.pass_check("含问题提纲")
    else:
        r.fail("未检测到问题提纲")

    question_count = count_pattern(workspace, f, r"^\s*(?:[-*]|\d+[.)]|Q\d+[:：])")
    if question_count < 5:
        r.warn(f"检测到 {question_count} 个问题条目，访谈提纲可能偏薄")
    else:
        r.pass_check(f"问题条目数: {question_count}")

    has_reminder = (
        file_contains_keyword(workspace, f, "访谈纪要")
        or file_contains_keyword(workspace, f, "原始记录")
        or file_contains_keyword(workspace, f, "notes")
    )
    if has_reminder:
        r.pass_check("含访谈后材料回收提示")
    else:
        r.warn("未检测到访谈纪要/原始记录回收提示")

    return r
