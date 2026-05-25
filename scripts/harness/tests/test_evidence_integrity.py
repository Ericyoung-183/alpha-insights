import sys
import tempfile
import unittest
from pathlib import Path


HARNESS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS_DIR))

from validators import stage3, stage4, stage5, stage6  # noqa: E402


def write_file(workspace, name, content):
    path = Path(workspace) / name
    path.write_text(content.strip() + "\n", encoding="utf-8")


def messages(result):
    data = result.to_dict()
    checks = [item["message"] for item in data["checks"]]
    warnings = data["warnings"]
    return checks + warnings


class EvidenceIntegrityGateTests(unittest.TestCase):
    def test_stage3_blocks_due_diligence_plan_without_primary_source_plan(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(
                workspace,
                "research_plan.md",
                """
# Research Plan

Scenario: due diligence / M&A target screening

Track A: Public records
Track B: Market research
Track C: Expert interview

H1: Target parent status is active.
Interview decision: no expert interview for this quick scan.
""",
            )

            result = stage3.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "BLOCKED ❌")
            self.assertTrue(
                any("primary-source plan" in msg for msg in messages(stage3.validate(workspace)))
            )

    def test_stage3_blocks_chinese_due_diligence_plan_with_negated_primary_source(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(
                workspace,
                "research_plan.md",
                """
# 研究计划

场景：标的公司尽调

Track A: Public records
Track B: Market research
Track C: Expert interview

H1: 标的公司母公司仍处于存续状态。
访谈决策：本轮快速扫描暂不访谈。
primary source: 未找到一手来源，先用企查查摘要。
""",
            )

            result = stage3.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "BLOCKED ❌")
            self.assertTrue(
                any("primary-source plan" in msg for msg in messages(stage3.validate(workspace)))
            )

    def test_stage3_accepts_due_diligence_plan_with_concrete_primary_source_path(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(
                workspace,
                "research_plan.md",
                """
# Research Plan

Scenario: due diligence target screening

Track A: Public records
Track B: Market research
Track C: Expert interview

H1: Target parent status is active.
Interview decision: no expert interview for this quick scan.

## primary-source plan
| Key fact | Primary source path |
| Entity status | official registry and regulatory filing |
""",
            )

            result = stage3.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "PASS ✅")
            self.assertTrue(
                any("primary-source plan" in msg for msg in messages(stage3.validate(workspace)))
            )

    def test_stage4_blocks_key_numbers_without_evidence_claim_ledger(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(workspace, "_state.json", '{"tier": 1}')
            write_file(
                workspace,
                "evidence_base.md",
                """
# Evidence Base

| A1-01 | B 级 | Track A | Market size reached RMB 100B in 2025 | source_type: official | source_date: 2025-01-10 |
| A1-02 | B 级 | Track A | Growth rate reached 20% in 2025 | source_type: official | source_date: 2025-01-10 |

## Framework analysis
Porter analysis recorded.
""",
            )

            result = stage4.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "BLOCKED ❌")
            self.assertTrue(
                any("Evidence Claim Ledger" in msg for msg in messages(stage4.validate(workspace)))
            )

    def test_stage4_blocks_empty_evidence_claim_ledger_section(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(workspace, "_state.json", '{"tier": 1}')
            write_file(
                workspace,
                "evidence_base.md",
                """
# Evidence Base

| A1-01 | B 级 | Track A | Market size reached RMB 100B in 2025 | source_type: official | source_date: 2025-01-10 |

## Evidence Claim Ledger

## Framework analysis
Porter analysis recorded.
""",
            )

            result = stage4.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "BLOCKED ❌")
            self.assertTrue(
                any("claim_id" in msg for msg in messages(stage4.validate(workspace)))
            )

    def test_stage4_allows_qualitative_evidence_without_key_claim_signal(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(workspace, "_state.json", '{"tier": 1}')
            write_file(
                workspace,
                "evidence_base.md",
                """
# Evidence Base

| A1-01 | B 级 | Track A | Competitors are increasing product bundling | source_type: expert | source_date: 2025-01-10 |
| A1-02 | B 级 | Track B | Users mention onboarding friction | source_type: expert | source_date: 2025-01-11 |

Line 1: qualitative support.
Line 2: qualitative support.
Line 3: qualitative support.
Line 4: qualitative support.
Line 5: qualitative support.

## Framework analysis
Porter analysis recorded.
""",
            )

            result = stage4.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "PASS ✅")
            self.assertTrue(
                any("未检测到 Evidence Claim Ledger" in msg for msg in messages(stage4.validate(workspace)))
            )

    def test_stage4_blocks_due_diligence_entity_claim_without_primary_source(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(workspace, "_state.json", '{"tier": 1}')
            write_file(
                workspace,
                "evidence_base.md",
                """
# Evidence Base

| A1-01 | B 级 | Track A | target parent is dissolved | source_type: aggregator | source_date: 2024-01-10 |

## Evidence Claim Ledger

claim_id: E-001
claim_type: entity
claim_text: Target parent is dissolved.
source_id: qcc-summary-001
source_type: aggregator
source_grade: B
source_date: 2024-01-10
retrieved_at: 2026-05-25
primary_source_required: true
primary_source_present: false
used_in: insight

## Framework analysis
Porter analysis recorded.
""",
            )

            result = stage4.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "BLOCKED ❌")
            self.assertTrue(
                any("primary source" in msg.lower() for msg in messages(stage4.validate(workspace)))
            )


    def test_stage5_blocks_strong_recommendation_backed_only_by_weak_sources(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(workspace, "_state.json", '{"tier": 1}')
            write_file(
                workspace,
                "insights.md",
                """
# Insights

Insight 1 score: 18 分
Red Team: substantive challenge recorded.
Blue Team: response recorded.
用户确认: 待确认
关键变量: regulatory filing freshness
So What -> implication -> strategy
So What -> implication -> strategy
So What -> implication -> strategy
Pre-mortem: filing may be stale.
SMART: Specific, Measurable, Achievable, Relevant, Time-bound.

Recommendation: strong recommendation to acquire the target immediately.
Evidence support: source grades C/D only.
""",
            )

            result = stage5.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "BLOCKED ❌")
            self.assertTrue(
                any("weak sources" in msg.lower() for msg in messages(stage5.validate(workspace)))
            )

    def test_stage4_blocks_aggregated_sources_repeating_same_origin(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(workspace, "_state.json", '{"tier": 1}')
            write_file(
                workspace,
                "evidence_base.md",
                """
# Evidence Base

| A1-01 | B 级 | Track A | market share reached 20% | source_type: aggregator | source_date: 2025-01-10 |

## Evidence Claim Ledger

claim_id: E-001
claim_type: numeric
claim_text: Target market share reached 20%.
value: 20%
unit: percent
period: 2025
source_id: media-001
source_type: aggregator
source_grade: B
source_date: 2025-01-10
retrieved_at: 2026-05-25
origin_id: original-report-2025
primary_source_required: false
primary_source_present: false
used_in: insight

claim_id: E-002
claim_type: numeric
claim_text: Target market share reached 20%.
value: 20%
unit: percent
period: 2025
source_id: media-002
source_type: aggregator
source_grade: B
source_date: 2025-02-01
retrieved_at: 2026-05-25
origin_id: original-report-2025
primary_source_required: false
primary_source_present: false
used_in: insight

## Framework analysis
Porter analysis recorded.
""",
            )

            result = stage4.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "BLOCKED ❌")
            self.assertTrue(
                any("source laundering risk" in msg.lower() for msg in messages(stage4.validate(workspace)))
            )


    def test_stage6_blocks_headline_number_and_chart_without_evidence_links(self):
        with tempfile.TemporaryDirectory() as workspace:
            write_file(workspace, "_state.json", '{"tier": 2}')
            body = """
<html>
<head><script src="echarts.min.js"></script></head>
<body>
<section id="cover-page"></section>
<section id="toc-page"></section>
<section class="chapter-section"><div class="chapter-header">Chapter 1</div></section>
<section id="footer-page"></section>
<div class="headline">Market size reached RMB 100B in 2025.</div>
<div id="chart1"></div><div id="chart2"></div><div id="chart3"></div>
<script>
const chart1 = echarts.init(document.getElementById('chart1'));
chart1.setOption({series: [{data: [100, 120]}]});
const chart2 = echarts.init(document.getElementById('chart2'));
chart2.setOption({series: [{data: [30, 40]}]});
const chart3 = echarts.init(document.getElementById('chart3'));
chart3.setOption({series: [{data: [10, 20]}]});
</script>
</body>
</html>
"""
            write_file(workspace, "report.html", body + ("x" * 5200))

            result = stage6.validate(workspace).to_dict()

            self.assertEqual(result["gate"], "BLOCKED ❌")
            self.assertTrue(
                any("evidence link" in msg.lower() for msg in messages(stage6.validate(workspace)))
            )


if __name__ == "__main__":
    unittest.main()
