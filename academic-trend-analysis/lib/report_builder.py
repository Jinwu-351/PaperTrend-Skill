"""趋势报告工具 — 构建 Prompt + 保存报告

功能:
- 构建趋势报告 Prompt（含所有论文摘要）
- 保存报告并自动追加 GB/T 7714 参考文献
- 引用编号重映射

完全自包含，无需外部 LLM API 或 Milvus。
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


# 知名会议/期刊集合
_TOP_VENUES = {
    "neurips", "nips", "icml", "iclr", "aaai", "ijcai", "rss", "corl",
    "nature machine intelligence", "science robotics",
    "jmlr", "tpami", "pami",
}


def _get_venue_tier(venue_or_source: str) -> str:
    if not venue_or_source:
        return ""
    v = venue_or_source.lower()
    if "workshop" in v:
        return "[workshop]"
    for top in _TOP_VENUES:
        if top in v:
            return "[顶会/顶刊]"
    if "arxiv" in v or "semantic_scholar" in v:
        return "[arXiv]"
    return ""


def _format_bibliography_entry(number: int, paper: Dict) -> str:
    """GB/T 7714 参考文献条目"""
    if not isinstance(paper, dict):
        return f"[{number}] 未知文献条目"

    title = paper.get("title", paper.get("file_name", paper.get("normalized_title", "Unknown")))
    authors = paper.get("authors", [])
    published = paper.get("published", "")
    venue = paper.get("venue", "")
    source = paper.get("source", "")
    entry_id = paper.get("entry_id", "")

    if isinstance(authors, str):
        try:
            parsed = json.loads(authors)
            authors = parsed if isinstance(parsed, list) else [authors]
        except (json.JSONDecodeError, TypeError):
            authors = [authors] if authors else []
    elif not isinstance(authors, list):
        authors = [str(authors)] if authors else []

    if not authors:
        author_str = "佚名"
    elif len(authors) <= 3:
        author_str = ", ".join(str(a) for a in authors)
    else:
        author_str = ", ".join(str(a) for a in authors[:3]) + ", 等"

    year = published[:4] if published and len(published) >= 4 else "n.d."
    source_info = venue if venue else (source if source else "arXiv preprint")

    url_suffix = ""
    if entry_id and entry_id.startswith("arxiv:"):
        # arXiv ID: "arxiv:2408.06520" → https://arxiv.org/abs/2408.06520
        url_suffix = f" https://arxiv.org/abs/{entry_id.split(':', 1)[1]}."
    elif entry_id and re.match(r'^10\.\d{4,}/', entry_id):
        # DOI: "10.1109/TIE.2024.3409901" → https://doi.org/10.1109/TIE.2024.3409901
        url_suffix = f" https://doi.org/{entry_id}."
    elif entry_id and re.match(r'^\d{4}\.\d{4,}', entry_id):
        # arXiv ID (old format): "2408.06520" → https://arxiv.org/abs/2408.06520
        url_suffix = f" https://arxiv.org/abs/{entry_id}."

    return f"[{number}] {author_str}. {title}[J]. {source_info}, {year}.{url_suffix}"


def validate_citations(report_content: str, all_papers: List[Dict]) -> List[Dict]:
    """验证报告中的引用是否与对应论文内容匹配

    策略：从正文上下文中提取英文技术术语（中文报告中通常嵌入英文术语），
    与对应论文标题+摘要做匹配。完全无重叠 → 标记为可疑引用。

    Args:
        report_content: 报告草稿的 Markdown 内容
        all_papers: 按 prompt 顺序排列的论文列表（core + supplement）

    Returns:
        可疑引用列表，每项包含 {citation_num, sentence, paper_title, matched_terms, verdict}
    """
    import re as _re

    body = report_content.split('## 参考文献')[0] if '## 参考文献' in report_content else report_content

    suspicious = []
    # 去重：相同 citation_num 只检查一次
    seen = set()

    for m in _re.finditer(r'(?<!\[)\[(\d+)\](?!\()', body):
        num = int(m.group(1))
        if num < 1 or num > len(all_papers) or num in seen:
            continue
        seen.add(num)

        paper = all_papers[num - 1]
        if not isinstance(paper, dict):
            continue

        # 提取引用所在句子（从上一个句号到下一个句号）
        before = body[:m.start()]
        after = body[m.end():]
        sent_start = before.rfind('。') + 1 if '。' in before else before.rfind('\n') + 1
        sent_end_idx = after.find('。')
        sent_end = m.end() + (sent_end_idx if sent_end_idx > 0 else min(200, len(after)))
        sentence = body[sent_start:sent_end].replace('\n', ' ').strip()

        # 跳过太短的句子（如纯列表项 "- **[N]** xxx"）
        if len(sentence) < 20:
            continue

        title = paper.get('title', '')
        summary = paper.get('summary', paper.get('content', ''))
        paper_text = f"{title} {summary}".lower()

        # 从句子中提取英文技术术语:
        # - 连续英文字母 ≥3 个的普通词 (如 "robot", "sensing")
        # - 2+ 大写字母组成的缩写词 (如 "RL", "SLAM", "TDCR", "HAVEN")
        en_terms_raw = _re.findall(r'[A-Za-z][a-z]{2,}|[A-Z]{2,}', sentence)
        # 过滤停用词，保留技术术语
        stopwords_lower = {
            'the','and','for','with','that','this','from','are','was',
            'has','had','its','not','but','all','can','may','use','used',
            'using','also','new','one','two','etc','via','per','based',
            'their','them','then','than','some','any','our','out',
            'have','been','were','will','would','could','should','each',
            'into','over','such','more','well','only','most','very',
            'just','now','see','get','set','put','way','day','end'}
        en_terms = []
        for t in en_terms_raw:
            tl = t.lower()
            if tl not in stopwords_lower and len(t) >= 2:
                en_terms.append(tl)

        if not en_terms:
            continue  # 纯中文句子，无法做跨语言验证

        # 检查匹配
        matched = [t for t in en_terms if t in paper_text]

        # 判断是否为"显著"英文术语（长词 ≥4 字母 或 全大写缩写）
        significant = [t for t in en_terms_raw
                      if len(t) >= 4 or (len(t) >= 2 and t.isupper())]

        # 含 ≥1 个显著术语但 0 匹配 → 可疑
        if len(significant) >= 1 and len(matched) == 0:
            suspicious.append({
                'citation_num': num,
                'sentence': sentence[:120],
                'paper_title': title[:100],
                'significant_terms': sorted(significant),
                'matched_terms': [],
                'verdict': 'SUSPICIOUS'
            })

    return suspicious


def _extract_core_concepts(demand: Dict) -> List[str]:
    """从 demand 数据提取核心研究概念"""
    concepts = set()
    for term in demand.get("query_terms", []):
        if term:
            concepts.add(term)
    web_summary = demand.get("web_summary", "")
    if web_summary:
        for m in re.findall(r'["""\*\*]([^""\*\*]{3,50})[\""\"\*\*]', web_summary):
            term = m.strip()
            if len(term) >= 3:
                concepts.add(term)
    return sorted(concepts)[:8]


def build_trend_prompt(user_query: str, core_papers: List[Dict],
                       supplement_papers: List[Dict], demand: Dict) -> str:
    """构建趋势报告 Prompt

    Args:
        user_query: 用户原始查询
        core_papers: 核心论文列表（含完整摘要）
        supplement_papers: 补充论文列表（仅元数据）
        demand: demand.json 数据

    Returns:
        完整的报告生成 Prompt
    """
    total = len(core_papers) + len(supplement_papers)
    start_date = demand.get("start_date", "")
    end_date = demand.get("end_date", "")
    date_range = f"{start_date} 至 {end_date}" if start_date and end_date else ""

    core_concepts = _extract_core_concepts(demand)

    lines = []
    lines.append(f"阅读提供的论文信息，并根据这些信息撰写一份学术前沿趋势洞察报告。")
    lines.append("")
    lines.append(f"**用户查询**: {user_query}")
    lines.append(f"**论文总数**: {total}")
    lines.append(f"**核心精读论文数**: {len(core_papers)}")
    if date_range:
        lines.append(f"**时间范围**: {date_range}")
    if core_concepts:
        lines.append(f"**该领域核心研究方向**（供聚类参考）：{', '.join(core_concepts)}")
    lines.append("")

    # 报告模板 — 放在最前面确保 LLM 注意
    template_path = Path(__file__).resolve().parent.parent / "templates" / "report_template.md"
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        lines.append("**报告结构模板**：严格按照以下模板结构撰写报告（{{...}} 为占位符，请根据论文摘要填充实际内容）：")
        lines.append("")
        lines.append(template_content)
        lines.append("")

    lines.append("**Constraints (约束条件)**")
    lines.append("")
    lines.append("### 证据层级（Evidence Hierarchy）")
    lines.append("1. **L1 — 论文直接结论**：论文摘要明确陈述的发现/数据，可直接引用，附带 `[N]` 编号。引用必须使用论文自身术语，不得替换概念（如不得将'单光子成像'替换为'事件相机'）。")
    lines.append("2. **L2 — 综合归纳**：基于 ≥2 篇论文证据的归纳性结论，标注 `[归纳]`，使用'总体而言''多篇论文表明'等语言。")
    lines.append("3. **L3 — 作者推断**：跨领域推测、工程判断、类比、假设，必须标注 `[推断]`，使用'可能''推测''有待验证'等修饰语。**L3 推断不得附带 `[N]` 引用编号**。")
    lines.append("")
    lines.append("### 跨论文对比禁止")
    lines.append("4. **禁止跨论文性能对比**：除非某篇论文自身做了跨方法对比实验，否则不得宣称 '方法 A 优于方法 B'。可分别陈述各方法的独立数据。跨方法推测必须以 `[推断]` 标注。")
    lines.append("")
    lines.append("### 引用与聚类")
    lines.append("5. **引用来源**：提及具体观点/方法/数据时须用 `[N]` 引用。编号对应下方列表序号，严禁使用不在列表中的编号。")
    lines.append("6. **逻辑聚类**：按方法/问题聚类分析，寻找共性与差异，不要逐篇总结。每个聚类方向须附分类标准说明。")
    lines.append("7. **重点分析**：优先深入分析标注 ★ 的核心论文，其余论文为补充引用。")
    lines.append("")
    lines.append("### 统计与负趋势")
    lines.append("8. **统计精确性**：论文数量须附分类标准（如'基于摘要关键词匹配'）。≤3 篇用精确数字，4-10 篇用'约'+数字，>10 篇用范围。注明统计方法论边界。")
    lines.append("9. **负趋势分析**：必须指出停滞/衰退方向和长期未解决问题。")
    lines.append("")
    lines.append("### 学术声明")
    lines.append("10. **报告末尾必须使用以下声明**：'本报告的事实性描述（标注 [N] 的引用）来源于引用文献的论文摘要。趋势分析、方法聚类与未来方向为作者基于文献证据的综合归纳与推断。推断性内容已标注 [推断]。部分趋势来自预印本研究，尚待同行评议验证。报告中的论文数量统计为基于摘要关键词的近似分类，不同分类标准可能导致不同计数。'")

    # 核心论文（含摘要）
    for i, paper in enumerate(core_papers, 1):
        title = paper.get("title", paper.get("normalized_title", paper.get("file_name", "Unknown")))
        authors = paper.get("authors", [])
        if isinstance(authors, list):
            author_str = ", ".join(authors[:3]) + (" 等" if len(authors) > 3 else "")
        else:
            author_str = str(authors) if authors else "Unknown"
        published = paper.get("published", "")
        venue = paper.get("venue", "")
        source = paper.get("source", "")
        summary = paper.get("summary", paper.get("content", ""))
        score = paper.get("score", "")
        display_venue = venue if venue else source
        tier_label = _get_venue_tier(venue or source)
        year = published[:4] if published and len(published) >= 4 else ""
        venue_info = f" ({display_venue}, {year}){tier_label}" if display_venue else f" ({year}){tier_label}" if year else ""
        score_info = f" | BM25 score: {score}" if score else ""

        lines.append("")
        lines.append(f"## [{i}] ★ {title}{venue_info}{score_info}")
        lines.append(f"作者: {author_str}")
        lines.append(f"发表时间: {published}")
        lines.append(f"摘要: {summary}")
        lines.append("─" * 60)

    # 补充论文（仅标题）
    offset = len(core_papers)
    for i, paper in enumerate(supplement_papers, 1):
        idx = offset + i
        title = paper.get("title", paper.get("normalized_title", paper.get("file_name", "Unknown")))
        authors = paper.get("authors", [])
        if isinstance(authors, list):
            author_str = authors[0] if authors else "Unknown"
        else:
            author_str = str(authors) if authors else "Unknown"
        published = paper.get("published", "")
        venue = paper.get("venue", "")
        source = paper.get("source", "")
        rrf = paper.get("rrf_score", "")
        display_venue = venue if venue else source
        tier_label = _get_venue_tier(venue or source)
        year = published[:4] if published and len(published) >= 4 else ""
        venue_info = f" ({display_venue}, {year}){tier_label}" if display_venue else f" ({year}){tier_label}" if year else ""
        rrf_info = f" | RRF score: {rrf}" if rrf else ""

        lines.append("")
        lines.append(f"## [{idx}] {title}{venue_info}{rrf_info}")
        lines.append(f"作者: {author_str}")
        lines.append(f"发表时间: {published}")

    lines.append("")
    lines.append("请生成趋势总结报告:")

    return "\n".join(lines)


def save_report(data_dir: Path, report_content: str, all_papers: List[Dict]) -> Path:
    """保存报告并自动追加 GB/T 7714 参考文献

    仅包含正文中实际引用的论文，并将 [N] 重映射为连续编号。

    Args:
        data_dir: session 数据目录
        report_content: 报告 Markdown 内容
        all_papers: 所有论文列表（core + supplement）

    Returns:
        报告文件路径
    """
    # 提取正文中所有 [N] 引用
    cited_indices = _extract_citation_indices(report_content)
    cited_set = set(cited_indices)

    # 构建重映射表：原始编号 → 连续编号
    remap = {old: new for new, old in enumerate(cited_indices, 1)}

    # 重映射正文中的引用编号
    report_content = _remap_citations(report_content, remap)

    # 生成参考文献：仅包含被引用的论文，使用连续编号
    bib_lines = ["\n---\n", "## 参考文献\n"]
    for i, paper in enumerate(all_papers, 1):
        if not isinstance(paper, dict):
            continue
        if i not in cited_set:
            continue
        entry = _format_bibliography_entry(remap[i], paper)
        bib_lines.append(entry)
        bib_lines.append("")

    report_content += "\n" + "\n".join(bib_lines)

    # 保存
    report_path = data_dir / "report.md"
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return report_path


def _remap_citations(text: str, remap: Dict[int, int]) -> str:
    """将正文中的 [N] 引用按 remap 表重映射为新编号。

    跳过两类不替换：
    - GB/T 7714 参考文献行（已在保存阶段，不应被替换）
    - Markdown 图片/链接: [text](url)
    """
    bib_pattern = re.compile(r'^\s*\[\d+\]\s+.*\[[JCMR]\]\.')
    lines = text.split('\n')
    remapped = []
    for line in lines:
        if bib_pattern.match(line):
            remapped.append(line)
            continue
        # 从后往前替换，避免偏移问题
        matches = list(re.finditer(r'\[(\d+)\]', line))
        if not matches:
            remapped.append(line)
            continue
        new_line = line
        for m in reversed(matches):
            # 跳过 Markdown 链接
            rest = new_line[m.end():m.end() + 1]
            if rest == '(':
                continue
            old_num = int(m.group(1))
            if old_num in remap:
                new_line = new_line[:m.start()] + f"[{remap[old_num]}]" + new_line[m.end():]
        remapped.append(new_line)
    return '\n'.join(remapped)


def _extract_citation_indices(text: str) -> list:
    """提取正文中所有 [N] 引用的编号。

    跳过两类误报：
    - GB/T 7714 参考文献行: [1] Author. Title...
    - Markdown 图片/链接: [text](url) 中的数字
    """
    cited = set()
    # 只匹配已生成的 GB/T 7714 行（含文献类型标记 [J]/[C]/[M]/[R]）
    bib_pattern = re.compile(r'^\s*\[\d+\]\s+.*\[[JCMR]\]\.')

    for line in text.split('\n'):
        if bib_pattern.match(line):
            continue
        for m in re.finditer(r'\[(\d+)\]', line):
            rest = line[m.end():m.end() + 1]
            if rest == '(':
                continue
            num = int(m.group(1))
            if 1 <= num <= 999:
                cited.add(num)
    return sorted(cited)
