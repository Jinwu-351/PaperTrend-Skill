# Workflow Stages — 详细定义

## Stage 1: 需求解析

**执行者**: `scripts/stage1_demand.py`

**输入**: 用户自然语言描述（如"分析 hierarchical reinforcement learning 的趋势"）

**输出**: `demand.json`

```json
{
  "task": "用户原始需求",
  "query": "hierarchical reinforcement learning",
  "query_terms": ["hierarchical reinforcement learning", "HRL", "option framework", "temporal abstraction", "skill discovery"],
  "max_results": 25,
  "start_date": "2024-05-27",
  "end_date": "2026-05-27",
  "web_summary": "领域背景总结（2-4 句）"
}
```

**规则**:
- `query_terms` 数量 3-5 个
- `start_date` 不早于 5 年前
- `end_date` 不晚于今天
- `web_summary` 必须有实质内容

## Stage 2: 论文搜索

**执行者**: `scripts/stage2_search.py` → `lib/paper_search.search_multi()`

**输入**: `demand.json` 中的 `query_terms`

**输出**: `paper_pre_list.json`

**搜索源**:
| 源 | API | 限制 |
|---|---|---|
| arXiv | XML API | 免费，需 3s 间隔 |
| Semantic Scholar | REST API | 100 req/5min |
| OpenAlex | REST API | 免费 |
| AlphaXiv | REST API | 免费 |

**去重策略**: DOI 匹配 + 标题归一化 + arXiv ID

## Stage 3: 摘要存储

**执行者**: `scripts/stage3_store.py` → `lib/paper_retrieval.AbstractStore`

**输入**: `paper_pre_list.json`

**输出**: `abstracts.json`

**机制**: JSON 文件存储，字段包含 title, authors, summary, published, venue, source 等

## Stage 4: 核心论文筛选

**执行者**: `scripts/stage4_select.py` → `lib/paper_retrieval.select_key_papers()`

**输入**: `abstracts.json` + `demand.json` 中的 `query`

**输出**: `core_papers.json`（默认 6 篇）

**算法**: BM25 检索 + 标题匹配 ×1.3 加分

## Stage 5: 补充论文检索

**执行者**: `scripts/stage5_supplement.py` → `lib/paper_retrieval.BM25Retriever.search_multi_rrf()`

**输入**: `abstracts.json` + `demand.json` 中的 `query_terms` + `core_papers.json`

**输出**: `supplement_papers.json`（默认 40 篇）

**算法**: 多关键词 BM25 检索 + RRF 排名融合，排除核心论文

## Stage 6: 构建 Prompt

**执行者**: `scripts/stage6_build_prompt.py` → `lib/report_builder.build_trend_prompt()`

**输入**: core_papers + supplement_papers + demand

**输出**: `report_prompt.md`

**内容**: 核心论文完整摘要 + 补充论文元数据 + 撰写要求 + 输出模板

## Stage 7: 撰写报告

**执行者**: Claude Code（按 `agents/trend_reporter.md` 指导）

**输入**: `report_prompt.md`

**输出**: `report_draft.md`

**要求**: 3000-5000 字，按方法聚类，必须包含负趋势分析

## Stage 8: 保存报告

**执行者**: `scripts/save_report.py`

**输入**: `report_draft.md` + 所有论文

**输出**: `report.md`

**处理**: 提取 `[N]` 引用 → 重映射为连续编号 → 生成 GB/T 7714 参考文献
