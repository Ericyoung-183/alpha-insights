"""Evidence and numeric integrity checks shared by stage validators."""

import os
import re


DUE_DILIGENCE_TERMS = (
    "due diligence",
    "m&a",
    "merger",
    "acquisition",
    "target screening",
    "corporate screening",
    "company background",
    "target company",
    "supplier screening",
    "supplier background",
    "尽调",
    "尽职调查",
    "企业尽调",
    "并购",
    "收购",
    "标的筛选",
    "标的研究",
    "标的公司",
    "公司背调",
    "供应商背调",
    "供应商审查",
)

PRIMARY_PLAN_LABEL_TERMS = (
    "primary-source plan",
    "primary source plan",
    "primary_source_plan",
    "一手源计划",
    "一手来源计划",
)

PRIMARY_PATH_TERMS = (
    "primary source",
    "primary-source",
    "primary_source",
    "official registry",
    "official register",
    "national register",
    "company registry",
    "regulatory filing",
    "regulatory record",
    "company disclosure",
    "court record",
    "sec filing",
    "一手源",
    "一手来源",
    "官方登记源",
    "官方来源",
    "工商登记",
    "监管备案",
    "监管记录",
    "企业公告",
    "公司披露",
    "法院记录",
    "原始备案",
)

PRIMARY_CONCRETE_PATH_TERMS = tuple(
    term for term in PRIMARY_PATH_TERMS
    if term not in {"primary source", "primary-source", "primary_source", "一手源", "一手来源"}
)

PRIMARY_NEGATION_PATTERN = re.compile(
    r"(no|without|missing|lack(?:ing)?|unavailable)\s+.{0,40}primary[- ]source|"
    r"primary[- ]source\s+.{0,40}(missing|unavailable|not found|absent)|"
    r"(无|没有|缺少|未找到).{0,20}(一手源|一手来源|官方来源|官方登记源|监管备案|公司披露)",
    re.IGNORECASE,
)

PRIMARY_SOURCE_TYPES = {
    "primary",
    "official",
    "official registry",
    "official_registry",
    "regulator",
    "regulatory",
    "regulatory_filing",
    "regulatory_record",
    "company_disclosure",
    "company disclosure",
    "company_registry",
    "filing",
    "court",
    "court_record",
}

AGGREGATED_SOURCE_TYPES = {
    "aggregator",
    "media",
    "third_party_summary",
    "third-party summary",
    "third party summary",
    "report_aggregator",
    "report aggregator",
    "summary",
}

ENTITY_CLAIM_TYPES = {
    "entity",
    "relationship",
    "filing",
    "litigation",
    "license",
    "officer",
    "ownership",
    "parent_status",
}


def _read(workspace, filename):
    path = os.path.join(workspace, filename)
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _lower(value):
    return (value or "").strip().lower()


def _truthy(value):
    return _lower(value) in {"true", "yes", "y", "1", "present", "是", "有"}


def _has_any(text, terms):
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _has_primary_source_plan(text):
    has_label = _has_any(text, PRIMARY_PLAN_LABEL_TERMS)
    if not has_label:
        return False
    if _has_any(text, PRIMARY_CONCRETE_PATH_TERMS):
        return True
    if PRIMARY_NEGATION_PATTERN.search(text):
        return False
    return _has_any(text, PRIMARY_PATH_TERMS)


def _field_map(block):
    fields = {}
    for match in re.finditer(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$", block, re.MULTILINE):
        fields[match.group(1).lower()] = match.group(2).strip()
    return fields


def _claim_blocks(text):
    blocks = []
    for match in re.finditer(r"(?ms)^\s*claim_id\s*:\s*.*?(?=^\s*claim_id\s*:|\Z)", text):
        fields = _field_map(match.group(0))
        if fields:
            blocks.append(fields)
    return blocks


def _used_in(fields, target):
    return target in _lower(fields.get("used_in"))


def _is_numeric_claim(fields):
    claim_type = _lower(fields.get("claim_type"))
    return claim_type == "numeric" or bool(fields.get("value"))


def _is_primary_source_type(source_type):
    normalized = _lower(source_type).replace("-", "_")
    return normalized in PRIMARY_SOURCE_TYPES or source_type in PRIMARY_SOURCE_TYPES


def _is_aggregated_source_type(source_type):
    normalized = _lower(source_type).replace("-", "_")
    return normalized in AGGREGATED_SOURCE_TYPES or source_type in AGGREGATED_SOURCE_TYPES


def validate_stage3_plan(r, workspace, filename="research_plan.md"):
    text = _read(workspace, filename)
    if not text or not _has_any(text, DUE_DILIGENCE_TERMS):
        return
    if _has_primary_source_plan(text):
        r.pass_check("尽调/标的筛选 primary-source plan 已声明")
    else:
        r.fail("尽调/标的筛选缺少 primary-source plan — 必须声明官方登记源/监管备案/公司披露等一手来源路径")


def validate_evidence_base(r, workspace, filename="evidence_base.md"):
    text = _read(workspace, filename)
    if not text:
        return

    claims = _claim_blocks(text)
    has_key_claim_signal = bool(re.search(
        r"headline|chart|关键数字|图表|市场规模|market size|增长率|growth rate|"
        r"份额|share|收入|revenue|gmv|亿元|亿|billion|million|%|"
        r"recommendation|strategic recommendation|关键建议|战略建议|行动建议|建议支撑",
        text,
        re.IGNORECASE,
    ))

    if "Evidence Claim Ledger" in text and not claims:
        r.fail("检测到 Evidence Claim Ledger 标题但未检测到 claim_id 字段")
        return
    if not claims and has_key_claim_signal:
        r.fail("关键数字/图表/建议支撑证据缺少 Evidence Claim Ledger claim_id 字段")
        return
    if not claims:
        r.warn("未检测到 Evidence Claim Ledger claim_id 字段 — 核心数字/实体事实建议结构化登记")
        return

    r.pass_check(f"Evidence Claim Ledger 条目: {len(claims)}")

    claim_origin_groups = {}
    for fields in claims:
        claim_id = fields.get("claim_id", "<unknown>")
        claim_type = _lower(fields.get("claim_type"))
        source_type = _lower(fields.get("source_type"))
        source_grade = _lower(fields.get("source_grade"))
        primary_required = _truthy(fields.get("primary_source_required"))
        primary_present = _truthy(fields.get("primary_source_present")) or _is_primary_source_type(source_type)
        used_for_headline_or_chart = _used_in(fields, "headline") or _used_in(fields, "chart")

        if primary_required and not primary_present:
            r.fail(f"{claim_id} requires primary source but primary_source_present is false")

        if claim_type in ENTITY_CLAIM_TYPES and _is_aggregated_source_type(source_type) and not primary_present:
            r.fail(f"{claim_id} entity/filing claim uses aggregated source without primary source")

        if (_is_numeric_claim(fields) or used_for_headline_or_chart) and used_for_headline_or_chart:
            if not fields.get("source_date"):
                r.fail(f"{claim_id} headline/chart claim missing source_date")
            if not fields.get("retrieved_at"):
                r.warn(f"{claim_id} headline/chart claim missing retrieved_at")

        if _is_numeric_claim(fields):
            missing = [name for name in ("unit", "period") if not fields.get(name)]
            value_text = " ".join([fields.get("value", ""), fields.get("claim_text", "")]).lower()
            if any(token in value_text for token in ("rmb", "usd", "$", "¥", "人民币", "美元")) and not fields.get("currency"):
                missing.append("currency")
            if missing:
                r.warn(f"{claim_id} numeric claim missing {', '.join(missing)}")

        if source_grade in {"a", "b"} and _is_aggregated_source_type(source_type) and not fields.get("origin_id"):
            r.warn(f"{claim_id} A/B graded aggregated source lacks origin_id — source laundering risk")

        key = re.sub(r"\s+", " ", _lower(fields.get("claim_text")))
        origin = _lower(fields.get("origin_id"))
        if key and _is_aggregated_source_type(source_type):
            claim_origin_groups.setdefault(key, []).append((claim_id, origin))

    for claim_text, entries in claim_origin_groups.items():
        origins = [origin for _, origin in entries if origin]
        if len(entries) >= 2 and (not origins or len(set(origins)) < len(entries)):
            ids = ", ".join(claim_id for claim_id, _ in entries)
            r.fail(f"source laundering risk: {ids} repeat the same or missing origin for '{claim_text[:60]}'")


def validate_insight_confidence(r, workspace, filename="insights.md"):
    text = _read(workspace, filename)
    if not text:
        return

    strong_recommendation = re.search(
        r"strong recommendation|strongly recommend|must acquire|immediately|明确建议|强烈建议|必须进入|立即收购|明确进入",
        text,
        re.IGNORECASE,
    )
    weak_only = re.search(
        r"source grades?\s*C\s*/\s*D\s*only|C/D\s*only|仅由\s*[CD]\s*级|只[由有].*[CD]\s*级",
        text,
        re.IGNORECASE,
    )
    explicit_high_grade = re.search(r"\bsource[_ ]?grades?\s*[:：]?\s*[AB]\b|[AB]\s*级", text, re.IGNORECASE)

    if strong_recommendation and (weak_only or not explicit_high_grade):
        r.fail("Strong recommendation backed only by weak sources — downgrade confidence or add A/B evidence")


def validate_report_links(r, workspace, filename="report.html"):
    text = _read(workspace, filename)
    if not text:
        return

    evidence_link_pattern = re.compile(
        r"claim[_-]?id|evidence[_-]?id|data-claim-id|data-evidence-id|source[_-]?id|evidence-ref|claimIds",
        re.IGNORECASE,
    )
    has_evidence_link = bool(evidence_link_pattern.search(text))

    headline_number = re.search(
        r"(headline|executive|summary|market size|核心数据|关键数字)[\s\S]{0,240}"
        r"(\d+(?:\.\d+)?\s*(?:%|bn|billion|million|rmb|usd|亿元|亿|万|美元|人民币))",
        text,
        re.IGNORECASE,
    )
    if headline_number and not has_evidence_link:
        r.fail("Headline number lacks evidence link — add claim_id/evidence_id/source_id")

    chart_data = "echarts.init" in text and re.search(r"(?i)(?:\"data\"|(?<!\")\bdata)\s*[:\[]", text)
    if chart_data and not has_evidence_link:
        r.fail("Chart data lacks evidence link — bind chart series to claim_id/evidence_id/source_id")
