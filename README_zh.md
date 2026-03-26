# Alpha Insights-BizAdvisor

> **一个把高阶商业分析师的底层思维和研究框架写进代码的超级 SKILL**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blue)](https://claude.ai/code)

---

## 简介

Alpha Insights 是一个专业的商业分析 AI 助手，旨在代替资深商业分析师产出有深度、有决策价值的研究报告。

**为什么选择 Alpha Insights？**

| 传统 AI 分析工具 | Alpha Insights |
|-----------------|----------------|
| 泛泛而谈，缺乏深度 | **结构化框架**驱动，19 个专业分析框架 |
| 输出不可追溯 | **证据链追溯**，每个结论标注来源和置信度 |
| 单一数据源 | **多轨道并行**搜索，三角验证法 |
| 一次性输出 | **交互式迭代**，持续深化洞察 |

**核心价值**：
- **L1 效率替代**：节省 60%+ 案头研究时间
- **L2 能力超越**：方法论驱动，输出质量对标 P7+ 分析师
- **L3 经验沉淀**：每次研究沉淀为知识资产

---

## 特性

### 底层思维（9 个方法论）

MECE 原则 | Issue Tree | 假设驱动 | 金字塔原理 | 三角验证 | 事前验尸 | 第一性原理 | ACH 竞争假设 | 专家访谈

### 研究框架（19 个）

**原创框架**：
- 3A战略八步法 — 从行业全景认知到战略决策收敛的完整方法论

**经典框架**：
- 战略分析：波特五力、价值链、SWOT、PESTEL、BCG 矩阵
- 商业模式：商业模式画布、平台画布、单位经济模型
- 市场分析：TAM/SAM/SOM、竞争定位图、行业生命周期
- 创新理论：颠覆式创新、蓝海战略、Jobs-to-be-Done
- 战略规划：Playing to Win、三层面模型、飞轮效应、SCP 范式

### 十大研究场景

| 场景 | 说明 |
|------|------|
| 🎯 行业研究 | 行业全景、市场规模、增长驱动力、产业链、关键玩家 |
| ⚔️ 竞争分析 | 竞争格局、对手策略、差异化定位、竞争应对 |
| 📱 产品分析 | 产品功能、用户体验、产品对比、产品迭代、产品定位 |
| 💼 商业模式分析 | 业务模式拆解、盈利逻辑、单位经济模型 |
| 🔍 商业机会挖掘 | 价值洼地、未满足需求、新兴趋势切入点 |
| 🌍 市场进入策略 | 新市场、新业务、可行性评估、进入路径 |
| 💰 投资决策支持 | 投资尽调、投资价值评估、估值分析、投资建议 |
| 📈 战略规划 | 年度规划、三年规划、战略目标、战略路径 |
| 🔒 尽职调查 | DD、风险排查、合规审查、背景调查 |
| ❓ 专项议题 | 政策解读、趋势判断、事件影响、决策咨询 |

---

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Ericyoung-179/alpha-insights.git

# 复制到 Claude Code Skills 目录
cp -r alpha-insights ~/.claude/Skills/
```

### 使用

在 Claude Code 中，直接提出商业分析问题即可自动触发：

```
用户：帮我分析一下中国新能源汽车充电桩行业的竞争格局
```

Alpha Insights 会自动：
1. 识别研究场景（竞争分析）
2. 选择合适框架（波特五力 + 竞争定位图）
3. 多轨道并行搜索数据
4. 生成结构化研究报告

---

## 数据源配置

### 🟢 开箱即用（无需配置）

| 数据源 | 说明 | 使用方式 |
|--------|------|---------|
| **公开渠道** | 行业报告、券商研报、财报、新闻、政策文件 | GoogleSearch + 网页抓取 |
| **专家访谈** | 定制提纲、记录模板、分析指引 | 方法论指导 |
| **小红书数据** | 消费者舆情、产品反馈、趋势洞察 | 内置脚本 + 内置公共 API Key（开箱即用）。如需使用自己的 Key，创建 `~/.alpha_insights.json` 并写入 `{"tikHubApiKey": "你的Key"}` |

### 🟡 可选扩展（需要配置）

| 数据源 | 说明 | 所需配置 |
|--------|------|---------|
| **知识库** | 历史研究报告、行业笔记 | Yuque MCP / Notion MCP |
| **内部数据** | 业务数据、用户行为 | ODPS MCP / 数据库 MCP |

> 未配置的数据源会自动跳过，不影响核心功能使用。

#### ODPS / 内部数据配置说明

SKILL 文件中（`resources/research_engine.md`、`resources/data_sources.md`）包含的 ODPS 表名和 SQL 示例来自特定部署环境，**你需要替换为自己的表名和字段**。搜索关键词 `odps.` 或 `antcc.` 即可定位所有需要修改的位置。

---

## 目录结构

```
alpha-insights/
├── SKILL.md              # 主文件（Skill 编排逻辑）
├── README.md             # 本文件
├── frameworks/           # 19 个战略框架
│   ├── 3a_8steps_strategy.md
│   ├── porters_five_forces.md
│   ├── swot.md
│   └── ...
├── methodology/          # 9 个方法论
│   ├── mece.md
│   ├── hypothesis_driven.md
│   ├── triangulation.md
│   └── ...
├── resources/            # 数据源、研究引擎、判断规则、反模式
│   ├── data_sources.md
│   ├── research_engine.md
│   ├── judgment_rules.md
│   └── anti_patterns.md
├── references/           # 报告标准、模板
│   ├── report_standards.md
│   └── report_template.html
└── scripts/              # 数据源脚本
    └── xhs/              # 小红书数据脚本
```

---

## 输出示例

Alpha Insights 生成的报告包含：

```
📊 研究报告结构
├── 执行摘要（1 页）
├── 核心发现（3-5 个）
├── 详细分析
│   ├── 行业概览
│   ├── 竞争格局
│   ├── 关键玩家画像
│   └── 机会与风险
├── 战略建议
└── 附录
    ├── 数据来源列表（A/B/C/D 分级）
    └── 证据库
```

**数据质量标注**：

| 级别 | 标准 | 置信度 |
|------|------|--------|
| A 级 | 3+ 独立来源交叉验证 | ✅ 高 |
| B 级 | 2 个来源交叉验证 | ✅ 可信赖 |
| C 级 | 单一权威来源 | ⚠️ 建议补充验证 |
| D 级 | 单一来源，可信度存疑 | ❌ 仅供参考 |

---

## 贡献指南

欢迎贡献！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

**贡献方向**：
- 新增分析框架
- 改进方法论文档
- 适配更多数据源
- 完善测试用例

---

## 许可证

MIT License

---

## 致谢

**经典框架来源**：
- Michael Porter（波特五力、价值链）
- Boston Consulting Group（BCG 矩阵）
- McKinsey & Company（三层面模型、假设驱动）
- Clayton Christensen（颠覆式创新、JTBD）
- Jim Collins（飞轮效应）
- Alexander Osterwalder（商业模式画布）

---

**作者**：Eric Yang + Claude
**原创框架**：3A战略八步法
**核心理念**：把方法论刻进代码里