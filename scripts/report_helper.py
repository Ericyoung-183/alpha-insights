#!/usr/bin/env python3
"""
report_helper.py — Alpha Insights 报告生成工具

两种使用方式：

1. build_report()（原始 API）：一次性传入所有 body HTML + charts，适合小报告。
2. ReportBuilder（推荐）：分步构建，解决大报告生成的两个核心问题：
   - 模板预填充：封面/目录/章节头/尾页自动生成，模型只填内容
   - 分步生成：save_state()/load_state() 支持多次调用，每次 2-3K tokens

ReportBuilder 用法：
    from report_helper import ReportBuilder

    b = ReportBuilder("报告标题", "副标题")
    b.set_toc_conclusion("核心结论一句话")

    b.add_chapter("01", "Executive Summary", "<h2>核心结论</h2><p>...</p>")
    b.add_chart("chart1", {"xAxis": {"type": "category", "values": [...]}, ...})

    b.add_chapter("02", "市场全景", "<h2>...</h2><p>...</p>")
    b.add_chart("chart2", {...})

    b.build("workspace/project/report.html")

分步生成（跨多次 Bash 调用）：
    # Step 1
    b = ReportBuilder("标题", "副标题")
    b.save_state("/tmp/rpt.json")

    # Step 2
    b = ReportBuilder.load_state("/tmp/rpt.json")
    b.add_chapter(...)
    b.save_state("/tmp/rpt.json")

    # Step N（最后一步）
    b = ReportBuilder.load_state("/tmp/rpt.json")
    b.build("workspace/project/report.html")

核心机制：模型在 Python dict 中使用 "values" 键（安全，不被输出层过滤），
本脚本在序列化为 ECharts JS 时自动映射 "values" → "data"。
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# ── 核心：values → data 安全序列化 ─────────────────────────────

def _to_js(obj, indent=0):
    """将 Python 对象递归序列化为 JS 对象字面量。
    
    关键：遇到 "values" 键时，输出为 "data"（ECharts 需要的键名）。
    这样模型永远不需要在 Python 代码中写出 "data" + 数组的模式。
    """
    pad = "  " * indent
    pad_inner = "  " * (indent + 1)
    
    if obj is None:
        return "null"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, (int, float)):
        return str(obj)
    elif isinstance(obj, str):
        # 转义字符串中的特殊字符
        escaped = obj.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        return f"'{escaped}'"
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        # 短数组（纯基本类型且长度 ≤ 8）单行输出
        if len(obj) <= 8 and all(isinstance(x, (int, float, str, bool, type(None))) for x in obj):
            items = ", ".join(_to_js(x) for x in obj)
            return f"[{items}]"
        # 长数组或含嵌套对象的数组，多行输出
        items = []
        for x in obj:
            items.append(f"{pad_inner}{_to_js(x, indent + 1)}")
        return "[\n" + ",\n".join(items) + f"\n{pad}]"
    elif isinstance(obj, dict):
        if not obj:
            return "{}"
        items = []
        for k, v in obj.items():
            # ★ 核心映射：values → data
            js_key = "data" if k == "values" else k
            # JS 对象键：简单标识符不加引号，其他加引号
            if re.match(r'^[a-zA-Z_$][a-zA-Z0-9_$]*$', js_key):
                key_str = js_key
            else:
                key_str = f"'{js_key}'"
            items.append(f"{pad_inner}{key_str}: {_to_js(v, indent + 1)}")
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    else:
        return str(obj)


# ── 图表 JS 生成 ──────────────────────────────────────────────

def _make_chart_js(charts):
    """生成所有 ECharts 初始化 JS 代码。

    每个图表用独立 try-catch 包裹，一个出错不影响其他图表。
    charts: list of dict, 每个 dict 含 "id" 和 "option" 键。
    """
    if not charts:
        return ""

    js_parts = []
    var_names = []
    for i, chart in enumerate(charts):
        chart_id = chart.get("id", f"chart{i+1}")
        option = chart.get("option", {})
        var_name = f"c{i+1}"
        var_names.append(var_name)

        # 每个图表独立 try-catch，防止一个出错杀死全部
        js_parts.append(
            f"var {var_name};\n"
            f"try {{\n"
            f"  {var_name} = echarts.init(document.getElementById('{chart_id}'));\n"
            f"  {var_name}.setOption({_to_js(option, 1)});\n"
            f"}} catch(e) {{\n"
            f"  console.error('ECharts init error [{chart_id}]:', e);\n"
            f"}}"
        )

    # 响应式 resize（也加保护）
    resize_lines = "".join(
        f"    if ({v}) {v}.resize();\n" for v in var_names
    )
    js_parts.append(
        f"window.addEventListener('resize', function() {{\n{resize_lines}}});"
    )

    return "\n\n".join(js_parts)


# ── 模板读取 ─────────────────────────────────────────────────

def _read_template(template_path=None):
    """读取 report_template.html，提取 <style> 和 ECharts CDN。"""
    if template_path is None:
        # 默认路径：相对于本脚本
        template_path = Path(__file__).parent.parent / "references" / "report_template.html"
    
    template_path = Path(template_path)
    if not template_path.exists():
        print(f"⚠️ 模板文件不存在: {template_path}，使用内置最小样式")
        return _minimal_style(), _ECHARTS_CDN, _FALLBACK_JS
    
    html = template_path.read_text(encoding="utf-8")
    
    # 提取 <style>...</style>
    style_match = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
    style = style_match.group(0) if style_match else "<style></style>"
    
    # 提取 ECharts CDN script 标签，强制加 crossorigin
    cdn_match = re.search(r'<script src="([^"]*echarts[^"]*)"[^>]*></script>', html)
    if cdn_match:
        cdn_url = cdn_match.group(1)
        cdn = f'<script src="{cdn_url}" crossorigin="anonymous"></script>'
    else:
        cdn = _ECHARTS_CDN
    
    # 提取 fallback JS
    fallback_match = re.search(
        r'<!-- 图表渲染 Fallback.*?</script>', html, re.DOTALL
    )
    fallback_js = fallback_match.group(0) if fallback_match else _FALLBACK_JS
    
    return style, cdn, fallback_js


_ECHARTS_CDN = '<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js" crossorigin="anonymous"></script>'

_FALLBACK_JS = '''<!-- 图表渲染 Fallback -->
<script>
  window.addEventListener('load', function() {
    if (typeof echarts === 'undefined') return;
    document.querySelectorAll('.chart-container > div[style*="height"]').forEach(function(el) {
      var instance = echarts.getInstanceByDom(el);
      if (!instance) {
        el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;min-height:200px;color:#94a3b8;font-size:14px;border:2px dashed #e2e8f0;border-radius:8px;padding:20px;text-align:center;">'
          + '<div>\\u26a0\\ufe0f 图表未能渲染<br><span style="font-size:12px;color:#cbd5e1;">可能原因：数据加载异常。请检查浏览器控制台。</span></div>'
          + '</div>';
      }
    });
  });
</script>'''


def _minimal_style():
    """模板不可用时的最小样式。"""
    return """<style>
  body { font-family: -apple-system, sans-serif; line-height: 1.6; color: #2D3748; background: #C9CED1; }
  .page { max-width: 900px; margin: 0 auto 20px; background: #fff; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
  .chart-container { margin: 20px 0; padding: 20px; background: #F1F5F9; border-radius: 8px; }
</style>"""


# ── 验证 ─────────────────────────────────────────────────────

def _validate(html, expected_charts):
    """验证生成的 HTML 中 ECharts 数据完整性。"""
    init_count = len(re.findall(r'echarts\.init', html))
    data_count = len(re.findall(r'\bdata\s*:', html))
    empty_data = len(re.findall(r'\bdata\s*:\s*\[\s*\]', html))
    
    print(f"[图表自检] ECharts 实例: {init_count}, data 键: {data_count}, 空数组: {empty_data}")
    
    ok = True
    if init_count != expected_charts:
        print(f"⚠️ 预期 {expected_charts} 个图表，实际 {init_count} 个 echarts.init")
        ok = False
    if data_count < init_count:
        print(f"⚠️ data 键数量({data_count}) < ECharts 实例数({init_count})，可能有数据丢失！")
        ok = False
    if empty_data > 0:
        print(f"⚠️ 发现 {empty_data} 个空数组，图表将无数据渲染！")
        ok = False
    if ok:
        print("✅ 图表数据完整性检查通过")
    return ok


# ── 主入口 ────────────────────────────────────────────────────

def build_report(
    body=None,
    body_file=None,
    charts=None,
    title="研究报告",
    output="report.html",
    template=None,
    confidential="内部资料",
    date=None,
):
    """
    组装完整报告 HTML 并写入文件。

    参数：
        body:         HTML 正文字符串（所有 <div class="page"> 块）
        body_file:    或者从文件读取正文（与 body 二选一）
        charts:       ECharts 图表配置列表，每个元素 {"id": "chart1", "option": {...}}
                      option 中用 "values" 替代 "data"
        title:        报告标题
        output:       输出文件路径
        template:     report_template.html 路径（None 使用默认）
        confidential: 保密级别
        date:         日期字符串（None 使用当天）
    """
    # 正文
    if body is None and body_file is not None:
        body = Path(body_file).read_text(encoding="utf-8")
    if body is None:
        body = ""
    
    # 日期
    if date is None:
        date = datetime.now().strftime("%Y年%m月%d日")
    
    # 模板资源
    style, cdn, fallback_js = _read_template(template)
    
    # 图表 JS
    chart_js = _make_chart_js(charts or [])
    chart_script = f"\n<script>\n{chart_js}\n</script>" if chart_js else ""
    
    # 组装
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  {style}
</head>
<body>

{body}

  <!-- 打印按钮 -->
  <div class="no-print">
    <button class="print-btn" onclick="window.print()">打印 / 导出 PDF</button>
  </div>

  {cdn}
  {chart_script}

  {fallback_js}

</body>
</html>"""
    
    # 写入
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    
    file_size = out_path.stat().st_size
    print(f"📄 报告已生成: {out_path} ({file_size:,} bytes)")
    
    # 验证
    if charts:
        _validate(html, len(charts))
    
    return str(out_path)


# ── ReportBuilder：分步构建 + 模板预填充 ────────────────────────

class ReportBuilder:
    """分步构建报告，解决大报告一次性生成的性能瓶颈。

    核心价值：
    1. 模板预填充 — 封面/目录/章节头/尾页自动生成，模型输出量减少 60-70%
    2. 分步生成 — save_state()/load_state() 支持跨多次 Bash 调用
    3. 自动图表管理 — add_chart() 自动处理 values→data 映射
    """

    def __init__(self, title="研究报告", subtitle="", date=None,
                 confidential="内部资料", version="V1.0",
                 author="Alpha Insights Research"):
        self.title = title
        self.subtitle = subtitle
        self.date = date or datetime.now().strftime("%Y年%m月%d日")
        self.confidential = confidential
        self.version = version
        self.author = author
        self.toc_conclusion = ""
        self.chapters = []   # list of [num_str, name, body_html]
        self.charts = []     # list of {"id": ..., "option": ...}

    # ── 内容添加 ──

    def set_toc_conclusion(self, text):
        """设置目录页的核心结论（1-2句话）。"""
        self.toc_conclusion = text
        return self

    def add_chapter(self, num, name, body_html):
        """添加一个章节。

        Args:
            num: 章节编号，如 "01"、1 或 3.5
            name: 章节名称，如 "Executive Summary"
            body_html: 章节内容 HTML（<div class="chapter-body"> 内部的内容）
                       可包含 h2/h3/p/table/highlight-box/stat-card/chart-container 等
        """
        if isinstance(num, float) and not num.is_integer():
            num_str = str(num)          # 3.5 → "3.5"
        elif isinstance(num, (int, float)):
            num_str = f"{int(num):02d}"  # 1 → "01", 3.0 → "03"
        else:
            num_str = str(num)           # "01" → "01"
        self.chapters.append([num_str, name, body_html])
        return self

    def add_chart(self, chart_id, option):
        """注册一个 ECharts 图表。

        Args:
            chart_id: 对应 HTML 中 <div id="chart_id"> 的 id
            option: ECharts option dict，用 "values" 替代 "data"
        """
        self.charts.append({"id": chart_id, "option": option})
        return self

    # ── 状态持久化（支持跨 Bash 调用的分步生成）──

    def save_state(self, path):
        """保存当前状态到 JSON 文件，下次 Bash 调用可 load_state() 恢复。"""
        state = {
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "date": self.date,
            "confidential": self.confidential,
            "version": self.version,
            "toc_conclusion": self.toc_conclusion,
            "chapters": self.chapters,
            "charts": self.charts,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"💾 状态已保存: {path} ({len(self.chapters)} 章, {len(self.charts)} 图表)")
        return self

    @classmethod
    def load_state(cls, path):
        """从 JSON 文件恢复 builder 状态。"""
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        builder = cls(
            title=state["title"],
            subtitle=state.get("subtitle", ""),
            author=state.get("author", "Alpha Insights Research"),
            date=state.get("date"),
            confidential=state.get("confidential", "内部资料"),
            version=state.get("version", "V1.0"),
        )
        builder.toc_conclusion = state.get("toc_conclusion", "")
        builder.chapters = state.get("chapters", [])
        builder.charts = state.get("charts", [])
        print(f"📂 状态已恢复: {len(builder.chapters)} 章, {len(builder.charts)} 图表")
        return builder

    # ── 模板生成（用户无需手写这些 HTML）──

    def _make_cover(self):
        return f'''<div class="page cover-page">
    <div class="cover-left">
      <div class="cover-number">AI</div>
    </div>
    <div class="cover-right">
      <div class="cover-badge">Alpha Insights - BizAdvisor</div>
      <h1 class="cover-title">{self.title}</h1>
      <p class="cover-subtitle">{self.subtitle}</p>
      <div class="cover-divider"></div>
      <p class="cover-meta">{self.author}</p>
      <p class="cover-date">{self.date}</p>
    </div>
    <div class="cover-footer">
      <span>{self.confidential}</span>
      <span>{self.version}</span>
    </div>
  </div>'''

    def _make_toc(self):
        items = "\n    ".join(
            f'<div class="toc-item">'
            f'<div class="toc-number">{ch[0]}</div>'
            f'<span class="toc-text">{ch[1]}</span>'
            f'</div>'
            for ch in self.chapters
        )
        conclusion = ""
        if self.toc_conclusion:
            conclusion = (
                f'<div class="toc-conclusion">'
                f'<div class="toc-conclusion-title">核心结论</div>'
                f'<div class="toc-conclusion-text">{self.toc_conclusion}</div>'
                f'</div>'
            )
        return f'''<div class="page toc-page">
    <div class="toc-header">
      <div class="toc-title">目 录</div>
    </div>
    {items}
    {conclusion}
  </div>'''

    def _make_chapter(self, num_str, name, body):
        return f'''<div class="page chapter-section">
    <div class="chapter-header">
      <div class="chapter-num">{num_str}</div>
      <div class="chapter-name">{name}</div>
    </div>
    <div class="chapter-body">
{body}
    </div>
  </div>'''

    def _make_footer(self):
        return f'''<div class="page footer-page">
    <div class="footer-content">
      <div class="footer-icon">📋</div>
      <div class="footer-title">{self.title}</div>
      <div class="footer-divider"></div>
      <div class="footer-text">本报告由 Alpha Insights-BizAdvisor 生成</div>
      <div class="footer-text">{self.confidential} · 请勿外传</div>
      <div class="footer-date">{self.date}</div>
      <div class="footer-cta">
        <a href="https://github.com/Ericyoung-183/alpha-insights" target="_blank">加星 ⭐ Alpha Insights → GitHub</a>
      </div>
    </div>
  </div>'''

    # ── 构建 ──

    def build(self, output, template=None):
        """组装所有章节并生成最终报告 HTML。

        Returns:
            输出文件路径字符串
        """
        # 组装 body
        parts = [self._make_cover(), self._make_toc()]
        for ch in self.chapters:
            parts.append(self._make_chapter(ch[0], ch[1], ch[2]))
        parts.append(self._make_footer())
        body = "\n\n".join(parts)

        # 调用 build_report 完成 HTML 组装 + 图表 JS 注入 + 验证
        return build_report(
            body=body,
            charts=self.charts,
            title=self.title,
            output=output,
            template=template,
            confidential=self.confidential,
            date=self.date,
        )


# ── CLI 入口 ─────────────────────────────────────────────────

if __name__ == "__main__":
    # 简单 CLI：python3 report_helper.py --body-file body.html --output report.html
    import argparse
    
    parser = argparse.ArgumentParser(description="Alpha Insights 报告生成器")
    parser.add_argument("--body-file", help="HTML 正文文件路径")
    parser.add_argument("--title", default="研究报告", help="报告标题")
    parser.add_argument("--output", default="report.html", help="输出路径")
    parser.add_argument("--template", help="模板路径")
    parser.add_argument("--confidential", default="内部资料", help="保密级别")
    args = parser.parse_args()
    
    build_report(
        body_file=args.body_file,
        title=args.title,
        output=args.output,
        template=args.template,
        confidential=args.confidential,
    )
