"""Stage 7: Iteration & Closure 验证器

Stage 7 无门控出口（终态），所有检查均为 advisory（WARN），不阻断。
核心新增职责：级联完整性验证——确保 Stage 7 迭代时，变更按级联链完整传递。
"""

import os

from .common import ValidationResult, file_exists, file_size_bytes, load_state


# Stage 7 级联链：上游 → 下游依赖顺序
CASCADE_CHAIN = [
    ("research_plan.md", 3, "research_definition.md", 2),
    ("evidence_base.md", 4, "research_plan.md", 3),
    ("insights.md", 5, "evidence_base.md", 4),
    ("report.html", 6, "insights.md", 5),
]

# mtime 允许误差（秒），抵消文件系统精度差异
MTIME_TOLERANCE = 60


def _get_mtime(workspace, filename):
    path = os.path.join(workspace, filename)
    if os.path.isfile(path):
        return os.path.getmtime(path)
    return None


def validate(workspace):
    r = ValidationResult(7)

    # ── 1. 基本存在性检查 ─────────────────────────
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

    # ── 2. 级联完整性检查 ─────────────────────────
    state = load_state(workspace)
    if state is None:
        r.warn("无法读取 _state.json，跳过级联完整性检查")
        return r

    current_stage = state.get("current_stage")
    if current_stage != 7:
        r.pass_check(f"当前 Stage {current_stage}，级联完整性检查仅在 Stage 7 执行")
        return r

    r.pass_check("_state.json 确认当前处于 Stage 7，执行级联完整性检查")

    upstream_updates = []
    chain_intact = True

    for downstream, ds_stage, upstream, us_stage in CASCADE_CHAIN:
        downstream_mtime = _get_mtime(workspace, downstream)
        upstream_mtime = _get_mtime(workspace, upstream)

        if downstream_mtime is None:
            # 下游文件不存在，级联链中断
            r.warn(f"级联链中断：阶段 {ds_stage} 产物 {downstream} 不存在（上游阶段 {us_stage} 产物 {upstream} 已存在）")
            chain_intact = False
            continue

        if upstream_mtime is None:
            # 上游不存在但下游存在，说明跳过了上游，勉强接受但提示
            r.warn(f"级联链异常：上游阶段 {us_stage} 产物 {upstream} 缺失，但下游 {downstream} 存在")
            chain_intact = False
            continue

        if upstream_mtime > downstream_mtime + MTIME_TOLERANCE:
            # 上游比下游新 → 级联不完整
            gap_sec = int(upstream_mtime - downstream_mtime)
            upstream_updates.append(f"阶段 {us_stage} 产物 {upstream} 比阶段 {ds_stage} 产物 {downstream} 新 {gap_sec}s")
            chain_intact = False
        else:
            r.pass_check(f"级联完整：{upstream} → {downstream}")

    if upstream_updates:
        for issue in upstream_updates:
            r.warn(f"级联不完整: {issue}")
        r.warn("级联规则：上游产物更新后，必须按级联链重新执行下游阶段（数据补充 S4→S5→S6 / 洞察调整 S5→S6 / 方向调整 S2→...→S6）")
    elif chain_intact:
        r.pass_check("级联完整性通过：所有上游产物时间戳 ≤ 下游产物，变更已完整传递")

    # ── 3. 迭代方向一致性检查 ───────────────────
    disclosure_log = state.get("disclosure_log", [])
    stage7_writes = [e for e in disclosure_log if e.get("stage") == 7 and e.get("type") == "file_load"]
    if stage7_writes:
        r.pass_check(f"Stage 7 迭代加载记录: {len(stage7_writes)} 次文件加载")

    return r
