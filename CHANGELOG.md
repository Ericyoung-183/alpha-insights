# Changelog

## V3.0.0 (2026-04-10)

> **质量保障体系重整 — 从散落的检查机制到风险驱动的统一框架**

### 质量保障体系
- 新增统一质量框架：7 审查角色工具箱 + 各 Stage 风险驱动质量配置表 + 失败处理 + 冲突处理原则
- 新增 Stage 3 假设自检（4 条标准：可证伪/有锐度/覆盖完整/可验证）
- 门控条件补全：IQR BLOCK 阻断（Stage 2/4/6）+ 访谈决策记录（Stage 3）
- 红蓝队执行流程明确化：上下文传递路径 + 硬性要求（无实质挑战不得写入 insights.md）
- 各质量工具降级方案：IQR / Dashboard / AskUserQuestion 在工具不可用时的替代路径
- Stage 5 精简：冗余规则列表和深度门控段移除（已在 judgment_rules.md 完整定义）

---

## V2.0.12 (2026-04-05)

> **访谈状态链路修复 + Validator/Dashboard 精度提升**

### 访谈状态记录链路修复
- SKILL.md Stage 3 访谈决策后新增 `state_manager.py log --type interview_activated/declined` 调用
- SKILL.md Stage 4 访谈催收检查点后新增 `state_manager.py log --type interview_checkpoint_done` 调用
- 根因：state_manager handler 已就绪、stage4 validator 已读取、Stage 6 互动引导已依赖，但 SKILL.md 从未指示模型写入 → `interview_activated` 永远为 false

### Validator 精度修复
- `stage5.py`：洞察计数 regex `[0-9#]` → `[I#]?\s*\d`，覆盖 `洞察 I1` 格式
- `dashboard.py`：评分提取前剥离 Markdown 粗体标记（`**`），修复 `= **19 分**` 格式无法匹配的问题

---

## V2.0.11 (2026-04-05)

> **XHS 端点 fallback 修复** — 小红书搜索恢复可用。

### XHS 脚本端点修复
- `search_notes.js`：补全 `app/search_notes` 端点到 fallback 列表，修复搜索返回空值
- 全部 4 个 XHS 脚本：删除"已被封禁"时效性注释，端点可用性随时变化，保持完整 fallback 列表自动适应
- 根因：上次修复错误判断"app 被反爬封禁"并移除 app 端点，实际是 web 端点失效、app 端点可用

---

## V2.0.10 (2026-04-04)

> **Stage 1 澄清提问优化** — 禁止在 Briefing 阶段询问研究维度，研究维度由 Stage 2 框架驱动自动生成。

### Stage 1 交互式澄清约束
- 明确提问方向：决策用途、目标受众、特定关注的公司/产品、地域/时间约束、已有认知或假设
- 禁止询问"关注哪些维度/方面"——避免越位 Stage 2 MECE 拆解、避免给用户设限
- 用户可在 Stage 2 确认研究定义时调整维度

---

## V2.0.9 (2026-04-04)

> **Hook 路径修复** — 修复所有用户 Hook 无法执行的阻断性问题。

### Hook 路径修复（阻断性 Bug）
- Frontmatter hooks 中 `${CLAUDE_SKILL_DIR}` → `${CLAUDE_PLUGIN_ROOT}`
- `${CLAUDE_PLUGIN_ROOT}` 在 hook command 中既做字符串替换又设为环境变量，指向 hook 所属 skill 目录
- 影响：4 个 hook 全部修复（html_write_guard、context_budget_hook、stage_gate_hook、progress_logger）
- 正文 `!` 内联命令保持 `${CLAUDE_SKILL_DIR}`（该上下文可正常展开）

---

## V2.0.8 (2026-04-04)

> **协议合规 & 状态机修复** — 第六轮 10 项质量检查，修复 Hook 协议、状态机 Stage 3.5、版本号、文档同步。

### Hook 协议合规
- `context_budget_hook.py`、`stage_gate_hook.py`：输出补 `"decision": "allow"` 字段，符合 Claude Code Hook 规范

### 状态机 Stage 3.5 支持
- `state_manager.py`：STAGE_NAMES 补 `3.5: "Interview"`，`advance --stage` 解析从 `int()` 改为 `float()`，支持 Stage 3→3.5→4 完整路径

### 版本号 & 文档同步
- SKILL.md 版本号从 V2.0.6 修正为 V2.0.8
- README_zh.md 目录树重写，补全 V2 Harness 子系统（harness/、report_helper、validators/、hooks/）
- B 级证据置信度标签统一为 ⚠️ 中等置信度（对齐 triangulation.md 权威定义）

### git-publish 裁剪规则首次全量执行（8 条）

---

## V2.0.7 (2026-04-04)

> **终极审计** — 6 轮 41 项检查，深入正则逻辑、状态机边界、报告管线集成、公开仓库信息安全。

### Validator 正则逻辑修复
- stage4/stage5：跨行匹配 `.*` → `[\s\S]*?`，修复框架结论检测和 So What 深度检测失效
- stage5：红蓝队 `8a`/`8b` 标记加 `\b` 词边界，防止章节编号误匹配

### 状态机边界补全
- `resume_check.py`：DELIVERABLES 补充 `3.5: interview_guides.md`，修复访谈阶段断点续研
- `compress_stage.py`：`_state.json` 读取加 try/except，符合 fail-open 原则

### 报告管线增强
- `ReportBuilder`：新增 `author` 参数（默认 "Alpha Insights Research"），替代硬编码

### GitHub 裁剪规则扩展（2 → 8 条）

---

## V2.0.6 (2026-04-04)

> **六层验证审计** — 从扫描式审查升级为验证式审查，8 批次修复 35 个问题（12 HIGH / 14 MEDIUM / 9 LOW），零回归。

### Tier 规则统一
- 所有档位执行全部 8 条分析规则 + 红蓝队审查 + IQR 复核，不因 Tier 降低分析深度
- ECharts 图表要求按 Tier 区分（Tier 2 ≥3 / Tier 3 ≥6）

### 门控↔验证器 100% 对齐
- SKILL.md 门控条件与 validator FAIL/WARN 级别完全一致
- evidence_base 行数按 Tier 区分（10/20/40 行）
- 封面/目录/尾页缺失从 WARN 升级为 FAIL
- B 级证据、访谈决策、红蓝队审查均为 FAIL 级校验

### 状态机加固
- `state_manager.py`：前进检查（禁止回跳）+ 访谈拒绝路径 + IQR 结果追踪 + Stage 3.5 交付物注册

### 路径系统统一
- 全文 `workspace/{project}` → `{ws}`（绝对路径），消除混用歧义
- Python 模板中 `{project}` → `{project_slug}` 统一
- ReportBuilder 代码模板使用 `os.path.join(ws, ...)` 消除占位符混淆

### 模板和定义补全
- Stage 3/3.5/4 新增输出格式模板（研究计划、访谈提纲、证据库结构）
- Layer 1/2/3 补充操作定义（谁执行、做什么、产出什么）
- 模糊指标量化：「数据源组合合理」→「覆盖 ≥80% 子问题」

### 执行机制增强
- IQR Subagent 调用规范（调用方式、结果处理、状态记录、降级方案）
- 红队致命挑战增加用户决策权（可接受修正或显式保留并标注）
- 多轨道失败决策规则（Track A 失败→阻断，其他 ≥2 失败→暂停询问）
- 档位升级路径细化（1→2、1→3、2→3 各需补充什么）
- 用户部分接受洞察处理规则
- Stage 7 验证器改为全 WARN（与「无门控出口」对齐）
- Stage 2 加载清单补充 `user_brief.md` 上下文恢复
- 上下文预算阈值文档化（70% warn / 90% block）

---

## V2.0 (2026-04-01)

> **核心升级理念**：Harness Engineering — 不过度投资 prompt，投资执行环境。通过脚本验证 + 状态机 + Hook 自动化 + 上下文压缩，从外部约束执行质量，把"AI 应该做"变成"系统保证做"。

### 新增：Harness 执行引擎（`scripts/harness/`）

**状态管理**
- `state_manager.py` — Workspace 初始化 + `_state.json` 状态机，追踪研究阶段、档位、框架加载、访谈状态等全流程元数据

**六阶段验证器**（`validators/stage1-6.py`）
- 每个 Stage 的交付物自动验证，PASS/FAIL/WARN 三级判定
- Tier 感知：Tier 2+ 对红蓝队审查、ECharts 图表数量等执行更严格的 FAIL 级校验
- Stage 5 验证器最为完善：评分检测 + 红蓝队审查 + 实质挑战 + So What 链深度 + Pre-mortem + SMART + 用户确认 + 关键变量 + 行动建议（共 13 项检查）

**Context 管理**
- `context_budget.py` — 估算 workspace 产物总 token 占用，预警 70%/90% 阈值
- `compress_stage.py` — 按 Stage 压缩产物（保留 A/B 级证据摘要），释放上下文空间

**质量仪表盘**
- `dashboard.py` — Stage 5→6 转场前，汇总 S2-S5 四阶段质量指标，一屏呈现

**会话恢复**
- `resume_check.py` — SKILL 加载时自动扫描进行中的研究 workspace，提示用户继续而非重新开始

### 新增：Hook 自动化系统

SKILL.md frontmatter 声明 4 个 Hook，平台自动执行：

| Hook | 触发时机 | 功能 |
|------|---------|------|
| `html_write_guard.py` | PreToolUse:Write | 阻止 Write 工具直接输出 HTML（必须用 Bash+Python） |
| `context_budget_hook.py` | PreToolUse:Read/Bash/Grep/Glob/Edit | 上下文预算实时预警，>90% 自动阻断 |
| `stage_gate_hook.py` | PostToolUse:Write | 写入交付物后自动运行门控验证 |
| `progress_logger.py` | PostToolUse:* | 异步记录工具调用日志（`_hook_log.jsonl`） |

共享模块：`_workspace_finder.py` — 从 cwd 智能定位 workspace 目录，支持多种回退策略。

### 新增：独立质量复核（IQR）

- `resources/quality_review.md` — Stage 2/4/6 三阶段 IQR 模板
- 独立 Subagent 评审，按 PASS/REVISE/BLOCK 处理
- Tier 2+ 自动触发

### 新增：ReportBuilder 分步生成器

- `scripts/report_helper.py` — `ReportBuilder` 类，分步构建 HTML 报告
- 自动生成封面、目录、章节头、尾页、ECharts 初始化代码
- `values→data` 自动映射，绕过模型输出层对 `data` 关键字的过滤
- 解决一次性生成大 HTML 的超时/截断问题

### 改进：SKILL.md V2.0 重构

**Stage 转场协议**
- 每个 Stage 开始时强制执行：Workspace 路径恢复 + Context 恢复 + 位置播报
- 每个 Stage 结束时强制输出标准化转场块
- 全阶段门控条件表（FAIL 阻断 + WARN 提示）

**Stage 1**
- 新增背景预研究（2-3 次快速搜索）+ 一句话结论播报（禁止展示原始搜索结果）
- 三档产出档位（Tier 1/2/3）正式纳入工作流，影响后续所有 Stage

**Stage 3**
- Q→H 映射规则：每个假设标注对应子问题，无假设的子问题注明原因
- 访谈决策纳入确认流程（不可跳过）

**Stage 4**
- 框架分析结论独立产出（新增检查项）
- 访谈催收检查点（Stage 3.5 激活时自动触发）
- 轨道跳过必须告知用户原因

**Stage 5**
- 深度门控：So What 链 ≥3 层 + Red-Team 必须产出 ≥1 个 Substantive 级挑战
- 逐规则播报（禁止黑箱合并执行）
- 用户确认前置到规则 7 后、红蓝队前

**Stage 6**
- HTML 必须通过 Bash+Python 生成（硬性规则，Hook 自动阻断 Write .html）
- ReportBuilder 分步生成（每步 1-2 章，避免超时）
- Tier 2+ 要求 ≥3 个 ECharts 交互图表（FAIL 级校验）

**Stage 7B 收尾**
- 精简收尾模板：议题 + 档位 + 报告路径 + 核心发现 + Star/Issue 链接

### 改进：数据源与搜索

- `resources/research_engine.md` — Track 标签统一修正（A→G），执行顺序明确
- XHS 脚本端点迁移（`check_topics.js`、`search_notes.js`、`get_note.js`）

### 改进：洞察质量

- `resources/judgment_rules.md` — insights.md 产出模板标准化，评分格式统一为 `= XX 分`
- 红蓝队 Subagent 模板细化，挑战分级（Fatal/Substantive/Weak/Addressable）

### 架构原则

- **优雅降级**：Bash 不可用时（如 Openclaw 环境），所有 Harness 功能回退到 V1 纯指令行为，不阻断工作流
- **Fail Open**：所有 Hook 和验证脚本在异常时静默放行
- **自包含**：禁止调用外部 SKILL，Alpha Insights 必须独立可用

### 文件清单

```
scripts/harness/
├── state_manager.py          # 状态机
├── stage_gate.py             # 验证器统一入口
├── context_budget.py         # 上下文预算分析
├── compress_stage.py         # 产物压缩
├── dashboard.py              # 质量仪表盘
├── resume_check.py           # 会话恢复
├── validators/
│   ├── __init__.py
│   ├── common.py             # 共享工具 + ValidationResult
│   ├── stage1.py ~ stage6.py # 六阶段验证器
└── hooks/
    ├── __init__.py
    ├── _workspace_finder.py  # 共享 workspace 定位
    ├── html_write_guard.py   # HTML 写入防护
    ├── context_budget_hook.py# 上下文预警
    ├── stage_gate_hook.py    # 自动门控
    └── progress_logger.py    # 进度日志

scripts/report_helper.py      # ReportBuilder + build_report()

resources/quality_review.md   # IQR 模板（新增）
```

---

## V1.0 (2026-03-26)

初始发布。七阶段工作流 + 19 框架 + 9 方法论 + 8 条判断力规则 + 三档产出 + HTML 报告。详见 [GitHub Release](https://github.com/Ericyoung-183/alpha-insights)。
