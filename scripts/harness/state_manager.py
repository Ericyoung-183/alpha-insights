#!/usr/bin/env python3
"""
Alpha Insights — Workspace State Manager

外部状态追踪，让 AI 的执行路径可审计。
管理 workspace/_state.json 文件。

用法:
    python3 state_manager.py init <workspace> --tier 2
    python3 state_manager.py advance <workspace> --stage 2
    python3 state_manager.py log <workspace> --type file_load --detail "📚 加载 X"
    python3 state_manager.py status <workspace>
"""

import json
import sys
import os
from datetime import datetime, timezone

STATE_FILE = "_state.json"
VERSION = "2.0"

STAGE_NAMES = {
    0: "Initialized",
    1: "Briefing",
    2: "Framing",
    3: "Planning",
    4: "Research",
    5: "Insights",
    6: "Report",
    7: "Iteration",
}

STAGE_DELIVERABLES = {
    1: "user_brief.md",
    2: "research_definition.md",
    3: "research_plan.md",
    3.5: "interview_guides.md",
    4: "evidence_base.md",
    5: "insights.md",
    6: "report.html",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _state_path(workspace):
    return os.path.join(workspace, STATE_FILE)


def _load_state(workspace):
    path = _state_path(workspace)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(json.dumps({"warning": f"_state.json 读取失败: {e}，视为不存在"}, ensure_ascii=False), file=sys.stderr)
        return None


def _save_state(workspace, state):
    state["updated_at"] = _now()
    path = _state_path(workspace)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def cmd_init(workspace, tier=3):
    """初始化 workspace 状态"""
    os.makedirs(workspace, exist_ok=True)
    state = {
        "version": VERSION,
        "workspace": os.path.abspath(workspace),
        "created_at": _now(),
        "updated_at": _now(),
        "tier": tier,
        "current_stage": 0,
        "completed_stages": [],
        "stage_history": [],
        "frameworks_loaded": [],
        "methodologies_loaded": [],
        "files_loaded": [],
        "disclosure_log": [],
        "validation_results": [],
        "stage_summaries": {},
        "interview_activated": False,
        "interview_checkpoint_done": False,
        "interview_checkpoint_result": None,
    }
    _save_state(workspace, state)
    print(json.dumps({"action": "init", "workspace": workspace, "tier": tier, "status": "OK ✅"}, ensure_ascii=False))


def cmd_advance(workspace, stage):
    """推进到指定 Stage"""
    state = _load_state(workspace)
    if state is None:
        print(json.dumps({"error": f"No _state.json in {workspace}. Run 'init' first."}, ensure_ascii=False))
        sys.exit(1)

    prev_stage = state["current_stage"]

    # 前进检查：禁止回跳（Stage 7 回退由 SKILL.md 边缘情况处理，不经 advance）
    if stage <= prev_stage and prev_stage > 0:
        print(json.dumps({
            "error": f"不允许从 Stage {prev_stage} 回跳到 Stage {stage}。如需回退，请使用 Stage 7 迭代流程。",
            "action": "advance",
            "status": "BLOCKED ❌",
        }, ensure_ascii=False))
        sys.exit(1)

    # 如果有前一个 Stage 在进行中，标记为完成
    if prev_stage > 0 and prev_stage not in state["completed_stages"]:
        state["completed_stages"].append(prev_stage)
        # 更新 stage_history 中最后一个条目的完成时间
        for entry in reversed(state["stage_history"]):
            if entry["stage"] == prev_stage and entry.get("completed") is None:
                entry["completed"] = _now()
                break

    state["current_stage"] = stage
    state["stage_history"].append({
        "stage": stage,
        "name": STAGE_NAMES.get(stage, f"Stage {stage}"),
        "started": _now(),
        "completed": None,
        "deliverable": STAGE_DELIVERABLES.get(stage),
    })

    _save_state(workspace, state)
    print(json.dumps({
        "action": "advance",
        "from_stage": prev_stage,
        "to_stage": stage,
        "stage_name": STAGE_NAMES.get(stage, f"Stage {stage}"),
        "status": "OK ✅",
    }, ensure_ascii=False))


def cmd_log(workspace, log_type, detail):
    """记录披露日志"""
    state = _load_state(workspace)
    if state is None:
        print(json.dumps({"error": f"No _state.json in {workspace}. Run 'init' first."}, ensure_ascii=False))
        sys.exit(1)

    entry = {
        "timestamp": _now(),
        "stage": state["current_stage"],
        "type": log_type,
        "detail": detail,
    }
    state["disclosure_log"].append(entry)

    # 自动追踪特定类型
    if log_type == "file_load":
        filename = detail.replace("📚 加载 ", "").replace("📚 加载", "").strip()
        if filename and filename not in state["files_loaded"]:
            state["files_loaded"].append(filename)
    elif log_type == "framework":
        if detail not in state["frameworks_loaded"]:
            state["frameworks_loaded"].append(detail)
    elif log_type == "methodology":
        if detail not in state["methodologies_loaded"]:
            state["methodologies_loaded"].append(detail)
    elif log_type == "interview_activated":
        state["interview_activated"] = True
    elif log_type == "interview_declined":
        state["interview_activated"] = False
    elif log_type == "interview_checkpoint_done":
        state["interview_checkpoint_done"] = True
        state["interview_checkpoint_result"] = detail  # "completed" / "deferred" / "cancelled"
    elif log_type == "iqr_result":
        # 记录 IQR 复核结果（PASS / REVISE / BLOCK）
        if "iqr_results" not in state:
            state["iqr_results"] = {}
        state["iqr_results"][str(state["current_stage"])] = {
            "result": detail,  # "PASS" / "REVISE" / "BLOCK"
            "timestamp": _now(),
        }

    _save_state(workspace, state)
    print(json.dumps({"action": "log", "entry": entry, "status": "OK ✅"}, ensure_ascii=False))


def cmd_status(workspace):
    """输出当前状态摘要"""
    state = _load_state(workspace)
    if state is None:
        print(json.dumps({"error": f"No _state.json in {workspace}."}, ensure_ascii=False))
        sys.exit(1)

    summary = {
        "tier": state["tier"],
        "current_stage": state["current_stage"],
        "current_stage_name": STAGE_NAMES.get(state["current_stage"], "Unknown"),
        "completed_stages": state["completed_stages"],
        "frameworks_loaded": len(state["frameworks_loaded"]),
        "methodologies_loaded": len(state["methodologies_loaded"]),
        "files_loaded": len(state["files_loaded"]),
        "disclosure_count": len(state["disclosure_log"]),
        "validation_results": state["validation_results"][-3:] if state["validation_results"] else [],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def cmd_record_validation(workspace, stage, result_json):
    """记录验证结果"""
    state = _load_state(workspace)
    if state is None:
        print(json.dumps({"error": f"No _state.json in {workspace}."}, ensure_ascii=False))
        sys.exit(1)

    result = json.loads(result_json) if isinstance(result_json, str) else result_json
    result["recorded_at"] = _now()
    state["validation_results"].append(result)
    _save_state(workspace, state)
    print(json.dumps({"action": "record_validation", "stage": stage, "status": "OK ✅"}, ensure_ascii=False))


def main():
    if len(sys.argv) < 3:
        print("用法: state_manager.py <command> <workspace> [options]")
        print("命令: init, advance, log, status, record_validation")
        sys.exit(1)

    command = sys.argv[1]
    workspace = sys.argv[2]

    if command == "init":
        tier = 3
        for i, arg in enumerate(sys.argv):
            if arg == "--tier" and i + 1 < len(sys.argv):
                tier = int(sys.argv[i + 1])
        cmd_init(workspace, tier)

    elif command == "advance":
        stage = None
        for i, arg in enumerate(sys.argv):
            if arg == "--stage" and i + 1 < len(sys.argv):
                stage = int(sys.argv[i + 1])
        if stage is None:
            print("错误: advance 需要 --stage N 参数")
            sys.exit(1)
        cmd_advance(workspace, stage)

    elif command == "log":
        log_type = None
        detail = None
        for i, arg in enumerate(sys.argv):
            if arg == "--type" and i + 1 < len(sys.argv):
                log_type = sys.argv[i + 1]
            if arg == "--detail" and i + 1 < len(sys.argv):
                detail = sys.argv[i + 1]
        if not log_type or not detail:
            print("错误: log 需要 --type 和 --detail 参数")
            sys.exit(1)
        cmd_log(workspace, log_type, detail)

    elif command == "status":
        cmd_status(workspace)

    elif command == "record_validation":
        stage = None
        result_json = None
        for i, arg in enumerate(sys.argv):
            if arg == "--stage" and i + 1 < len(sys.argv):
                stage = int(sys.argv[i + 1])
            if arg == "--result" and i + 1 < len(sys.argv):
                result_json = sys.argv[i + 1]
        if stage is None or result_json is None:
            print("错误: record_validation 需要 --stage 和 --result 参数")
            sys.exit(1)
        cmd_record_validation(workspace, stage, result_json)

    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
