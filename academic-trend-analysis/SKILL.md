---
name: academic-trend-analysis
description: |
  学术论文趋势分析工作流。端到端完成：需求解析 → 多源论文搜索 → 去重 →
  摘要存储与检索 → 核心论文筛选 → 趋势报告生成。
  Use when: (1) 用户要求分析某个研究方向/领域的趋势、前沿、热点
  (2) 用户说"分析 X 的趋势"、"X 领域的论文调研"、"X 方向的研究动态"
  (3) 用户需要搜索论文、生成学术报告、文献综述
  (4) 用户触发 /academic-trend-analysis 命令
  Triggers: "趋势", "前沿", "热点", "论文调研", "文献综述", "research trend",
  "academic survey", "paper search", "论文搜索", "趋势分析", "领域分析",
  "research landscape", "literature review"
---

# Academic Trend Analysis — 学术论文趋势分析

> 🛑 🛑 🛑 **MANDATORY INTERACTION CHECKPOINTS — 不可跳过！**
>
> 以下 3 个节点**必须停止并等待用户回复**，其余全部自动执行。
> 跳过任一检查点将导致后续脚本拒绝执行（`sys.exit(1)`）。
>
> | # | 检查点 | 何时停止 | 等待什么 | 如何继续 |
> |---|--------|---------|---------|---------|
> | 1 | **Stage 0 → 1** | 两种模式都可用时 | 用户输入 `1`（BM25）或 `2`（Milvus） | 拿到选择后进入 Stage 1 |
> | 2 | **Stage 1 内部** | WebSearch 完成后 | 向用户提 2-3 个澄清问题，等回复 | 拿到回复后构建 demand.json |
> | 3 | **Stage 1 → 2** | demand.json 生成后 | 展示内容，等用户说「继续」/「confirm」 | 用户确认后运行 `stage1_demand.py ... --confirm` 设置 `user_confirmed: true` |
>
> **Stage 2-8 全部自动执行**，每步完成后展示结果即可，不需等待。
> 用户可在 Stage 1 确认后说「继续执行完」，此时一次性执行 Stage 2-8。
>
> ⚠️ **如果跳过检查点直接运行 Stage 2+，脚本会输出 `🛑 GUARD BLOCKED` 并退出。**
>
> 详见 [`references/interaction-guide.md`](references/interaction-guide.md)。

端到端学术趋势分析工作流，基于多源论文搜索 + BM25 检索 + Claude Code 推理，
生成带有 GB/T 7714 参考文献的趋势分析报告。

**自包含设计**: 所有代码在 `lib/` 和 `scripts/` 目录中，无需外部依赖（仅需 `requests`），可在任何环境运行。

## 交互原则

> 本流程中仅以下 3 个节点需要**停止并等待用户确认**：
>
> | 节点 | 条件 | 动作 |
> |------|------|------|
> | Stage 0 → 1 | 两种模式都可用 | 展示选择，等待用户选 1/2 |
> | Stage 1 内部 | WebSearch 完成 | 提出 2-3 个澄清问题，等待回复 |
> | Stage 1 → 2 | demand.json 生成 | 展示内容，等待"继续"确认 |
>
> **其余 Stage（2-8）为自动化步骤**，完成后向用户展示结果即可，不需要停止等待。
> 用户可在 Stage 1 确认后说"继续执行完"，此时一次性执行 Stage 2-8。
>
> 详见 [`references/interaction-guide.md`](references/interaction-guide.md)。

## Quick Start

```
分析 hierarchical reinforcement learning 的趋势
```

→ Claude Code 首先执行 **Stage 0（环境探测 + 模式确认）**，确认本次使用 BM25 还是 Milvus 后，
再从 Stage 1 开始按阶段逐步执行，最终输出 `report.md`。

**执行方式**: Claude Code 按 `agents/` 目录下的指导文件逐步编排。
Stage 0/1 含交互检查点（⛔），Stage 2-8 自动执行，每步完成后展示结果。

> ⚠️ **模式必须在 Stage 0 一次性确认**：模式写入 `demand.json.mode` 后，
> Stage 3/4/5 全部自动复用，避免中途切换导致数据/索引不一致。

---

## Pipeline Stages

| Stage | 名称 | 执行方式 | 输出 | 交互 |
|-------|------|----------|------|------|
| 0 | 环境探测 + 模式确认 | Claude Code + `scripts/stage0_mode.py` | 终端报告 | ⛔ 条件性确认 |
| 1 | 需求解析 | Claude Code + `scripts/stage1_demand.py` | `demand.json`（含 `mode`） | ⛔ 需求澄清 + 确认 |
| 2 | 论文搜索 | `scripts/stage2_search.py` | `paper_pre_list.json` | 自动 → 展示结果 |
| 3 | 摘要存储 | `scripts/stage3_store.py` | `abstracts.json` | 自动 → 展示结果 |
| 4 | 核心论文筛选 | `scripts/stage4_select.py` | `core_papers.json` | 自动 → 展示结果 |
| 5 | 补充论文检索 | `scripts/stage5_supplement.py` | `supplement_papers.json` | 自动 → 展示结果 |
| 5.5 | 文献质量分级 | `scripts/stage5_5_quality_tier.py` | `quality_tiers.json` | 自动 → 展示结果 |
| 6 | 构建 Prompt | `scripts/stage6_build_prompt.py` | `report_prompt.md` | 自动 → 展示结果 |
| 7 | 撰写报告 | Claude Code 阅读 prompt 撰写 | `report_draft.md` | 自动 → 展示结果 |
| 8 | 保存报告 | `scripts/save_report.py` | `report.md` | 自动 → 展示结果 |

### 状态机

```
START
  │
  ▼
┌─────────────┐
│ Stage 0     │  环境探测 → 推荐模式
│ Claude Code │  ⛔ 两种模式可用时: 用户确认
└──────┬──────┘  仅一种可用时: 自动继续
       ▼
┌─────────────┐
│ Stage 1     │  WebSearch → ⛔ 提问题 → 等回复
│ Claude Code │  → 缺口分析 → demand.json → ⛔ 用户确认
└──────┬──────┘
       ▼
┌─────────────┐
│ Stage 2-8   │  自动执行（搜索→存储→筛选→补充→分级
│ auto        │  →Prompt→撰写→保存），每步完成后展示结果
└──────┬──────┘
       ▼
     DONE
```

---

## Agent Team

| # | Agent | 角色 | 文件 |
|---|-------|------|------|
| 0 | `mode_selector` | 模式选择器（前置） | [`agents/mode_selector.md`](agents/mode_selector.md) |
| 1 | `demand_analyzer` | 需求分析师 | [`agents/demand_analyzer.md`](agents/demand_analyzer.md) |
| 2 | `paper_searcher` | 论文搜索员 | [`agents/paper_searcher.md`](agents/paper_searcher.md) |
| 3 | `knowledge_manager` | 知识管理员 | [`agents/knowledge_manager.md`](agents/knowledge_manager.md) |
| 4 | `trend_reporter` | 趋势报告员 | [`agents/trend_reporter.md`](agents/trend_reporter.md) |

---

## 执行流程

Claude Code 按以下步骤逐步执行：

### Stage 0: 环境探测 + 模式确认（**必须前置**）

```bash
python academic-trend-analysis/scripts/stage0_mode.py            # 人类可读报告
python academic-trend-analysis/scripts/stage0_mode.py --json     # JSON 结构（程序化）
```

输出包含：
- 当前环境是否安装 `pymilvus` / `sentence-transformers`
- 是否检测到本地 Milvus 数据库及已有 collection
- 推荐模式（基于环境）

Claude Code 将报告展示给用户。

⛔ **STOP（条件性）**：如果 BM25 和 Milvus 两种模式都可用，
必须等待用户选择模式后再进入 Stage 1。
如果只有一种模式可用，直接使用该模式进入 Stage 1，不需要等待。

**确认后的模式作为 `--mode` 传入 Stage 1，会写入 `demand.json.mode`**。

### Stage 1: 需求解析

Claude Code **必须**先执行以下步骤，再运行脚本：

1. **WebSearch** 搜索 `"{query} research trends latest advances 2025 2026"`，获取领域背景
   - 如果搜索失败（≥3 次），向用户报告并请求手动提供领域背景信息
2. ⛔ **STOP**：向用户提出 2-3 个澄清问题，**等待回复**
3. 基于搜索结果 + 用户回复构造 `query_terms` 和 `web_summary`

然后传入脚本：

```bash
python academic-trend-analysis/scripts/stage1_demand.py "研究方向关键词" [data_dir] \
    --mode <bm25|milvus> \
    --query_terms "term1" "term2" "term3" \
    --web_summary "基于网络搜索的领域背景摘要，2-4 句"
```

> ⚠️ `--query_terms` 和 `--web_summary` 应来自真实调研。
> 若省略，脚本会 fallback 到内置模板，但输出 ⚠️ 质量警告。

生成 `demand.json`，包含扩展关键词、时间范围、领域背景摘要、**mode 字段**。

⛔ **STOP**：完成后向用户展示 demand.json 内容，等待"继续"确认后再进入 Stage 2。

### Stage 2: 论文搜索（自动执行 → 完成后展示结果）

```bash
python academic-trend-analysis/scripts/stage2_search.py <data_dir> [--max_results 25]
```

从 `demand.json` 读取关键词，搜索四源论文并去重。
完成后向用户展示：来源分布 + 去重前后数量。

### Stage 3: 摘要存储（自动执行 → 完成后展示结果）

```bash
python academic-trend-analysis/scripts/stage3_store.py <data_dir>
```

**自动从 `demand.json.mode` 读取模式**，无需再传 `--mode`。
BM25 模式使用 JSON 文件存储；Milvus 模式需要 `pymilvus` + `sentence-transformers`。
如需临时覆盖：`python academic-trend-analysis/scripts/stage3_store.py <data_dir> --mode milvus`。

### Stage 4: 核心论文筛选（自动执行 → 完成后展示结果）

```bash
python academic-trend-analysis/scripts/stage4_select.py <data_dir> [--limit 12]
```

根据 `demand.json` 中的 query 从摘要库中筛选最相关的论文。mode 自动读取。

### Stage 5: 补充论文检索（自动执行 → 完成后展示结果）

```bash
python academic-trend-analysis/scripts/stage5_supplement.py <data_dir> [--top_k 50]
```

多关键词 RRF 融合检索，排除核心论文。mode 自动读取。

### Stage 5.5: 文献质量分级（自动执行 → 完成后展示结果）

```bash
python academic-trend-analysis/scripts/stage5_5_quality_tier.py <data_dir>
```

对**核心论文 + 补充论文全体**进行 **T1/T2/T3** 三级质量标注，生成 `quality_tiers.json`：

| 分级 | 含义 | 判定规则 |
|------|------|---------|
| **T1** | 经同行评议 | 发表于 IEEE Trans、ICRA、IJCAI 等已知会议/期刊 |
| **T2** | 预印本（未评议） | 来源为 arXiv/bioRxiv 等预印本平台 |
| **T3** | 来源待核实 | 来源为 Semantic Scholar/OpenAlex 且无已知 venue |

**Claude Code** 展示分级报告给用户，若 T2+T3 占比过高（>60%），须在报告中加入质量声明。

### Stage 6: 构建 Prompt（自动执行 → 完成后展示结果）

```bash
python academic-trend-analysis/scripts/stage6_build_prompt.py <data_dir>
```

合并核心论文摘要和补充论文元数据，构建报告生成 Prompt。

### Stage 7: 撰写报告（自动执行 → 完成后展示结果）

Claude Code 读取 `report_prompt.md`，按撰写要求生成 `report_draft.md`。
完成后向用户展示报告路径和概要。

### Stage 8: 保存报告（自动执行 → 完成后展示结果）

```bash
python academic-trend-analysis/scripts/save_report.py <data_dir> <report_draft_path>
```

自动提取引用、重映射编号、追加 GB/T 7714 参考文献。

### Python API

```python
import sys
from pathlib import Path
sys.path.insert(0, "academic-trend-analysis/lib")

from paper_search import search_multi, save_papers, expand_query_terms, generate_web_summary
from paper_retrieval import AbstractStore, select_key_papers, BM25Retriever
from report_builder import build_trend_prompt, save_report

data_dir = Path("data/my-session")

# 搜索
papers, deduped, _ = search_multi(["keyword1", "keyword2"], max_results=25)
save_papers(data_dir, deduped)

# 存储
store = AbstractStore(data_dir)
store.add_batch(deduped)
store.save()

# 核心论文
core = select_key_papers(store, "keyword", limit=12)

# 补充检索
retriever = BM25Retriever()
retriever.build_index(store.all_papers())
supplement = retriever.search_multi_rrf(["kw1", "kw2"], top_k=50)

# 构建 prompt
prompt = build_trend_prompt("keyword", core, supplement, demand)
```

---

## Session Data Directory

```
data/2026-05-27-15-31/
├── demand.json              # 结构化需求
├── paper_pre_list.json      # 搜索结果（去重后）
├── abstracts.json           # 摘要存储
├── core_papers.json         # 核心论文（含 BM25 score）
├── quality_tiers.json       # 文献质量分级报告
├── supplement_papers.json   # 补充论文（含 RRF score）
├── report_prompt.md         # 报告生成 Prompt
├── report_draft.md          # 报告草稿（Claude Code 撰写）
└── report.md                # 最终报告（含参考文献）
```

---

## 技术架构

### 两种检索模式

| 模式 | 依赖 | 检索方式 | 适用场景 |
|------|------|---------|---------|
| **BM25**（默认） | Python 标准库 + `requests` | 关键词 BM25 匹配 | 首次使用、快速验证、零配置环境 |
| **Milvus** | `pymilvus` + `sentence-transformers` + embedding 模型 | 向量余弦相似度 + 查询扩展 | 需要语义召回、追求最高检索质量 |

### 各模式实现

| 组件 | BM25 | Milvus |
|------|------|--------|
| 论文搜索 | `lib/paper_search.py` | `lib/paper_search.py` |
| 去重 | `lib/paper_search.py` | `lib/paper_search.py` |
| 摘要存储 | `lib/paper_retrieval.py` — JSON 文件 | `lib/paper_retrieval.py` — Milvus 向量 |
| 检索 | `lib/paper_retrieval.py` — BM25 | `lib/paper_retrieval.py` — BGE embedding |
| RRF 融合 | `lib/paper_retrieval.py` — 纯 Python | `lib/paper_retrieval.py` — 向量 RRF |
| 报告生成 | `lib/report_builder.py` | `lib/report_builder.py` |
| LLM | **Claude Code** — 直接撰写 | **Claude Code** — 直接撰写 |

### 依赖

- `requests` — HTTP 请求（论文搜索 API）
- Python 标准库 — `json`, `xml.etree`, `re`, `math`, `collections`
- Milvus 模式额外依赖：`pymilvus`, `sentence-transformers`

### 不适用 Milvus 的说明

BM25 对学术论文摘要的检索效果与轻量向量检索相当，且零依赖、零配置。
优先使用 BM25 模式，仅在需要语义召回时切换到 Milvus。

---

## Key Constraints

1. **模式前置**：必须在 Stage 0 完成模式确认并写入 `demand.json.mode`，全流程一致，禁止中途切换
2. **摘要来源**：所有结论基于论文摘要，不编造
3. **搜索限制**：关键词 5-8 个（经缺口分析和语义重叠检查），每源 ≤ 25 篇
4. **引用连续**：[N] 编号 ≤ 论文总数，严格对应
5. **必须负趋势**：报告必须包含负趋势分析

---

## File Structure

```
academic-trend-analysis/
├── SKILL.md                          # 本文件
├── agents/
│   ├── mode_selector.md              # 模式选择器（Stage 0 前置）
│   ├── demand_analyzer.md            # 需求分析师
│   ├── paper_searcher.md             # 论文搜索员
│   ├── knowledge_manager.md          # 知识管理员
│   └── trend_reporter.md             # 趋势报告员
├── lib/                              # 自包含代码库
│   ├── __init__.py
│   ├── paper_search.py               # 多源搜索 + 去重 + 关键词扩展
│   ├── paper_retrieval.py            # BM25/Milvus 检索 + 摘要存储
│   └── report_builder.py             # Prompt 构建 + 报告保存
├── scripts/
│   ├── stage0_mode.py                # Stage 0: 环境探测 + 模式推荐
│   ├── _mode_resolver.py             # 共享：mode 解析（CLI > demand.json > default）
│   ├── stage1_demand.py              # Stage 1: 需求解析（写入 mode）
│   ├── stage2_search.py              # Stage 2: 论文搜索 + 去重
│   ├── stage3_store.py               # Stage 3: 摘要入库（自动读 mode）
│   ├── stage4_select.py              # Stage 4: 核心论文筛选（自动读 mode）
│   ├── stage5_supplement.py          # Stage 5: 补充论文 RRF 检索（自动读 mode）
│   ├── stage6_build_prompt.py        # Stage 6: 构建报告 Prompt
│   └── save_report.py                # Stage 8: 保存报告（含参考文献）
├── references/
│   ├── workflow.md                   # 阶段详细定义
│   ├── rag-architecture.md           # 技术架构说明
│   └── interaction-guide.md          # 交互检查点指南
├── templates/
│   └── report_template.md            # 报告生成模板（8 段式结构）
└── examples/
    └── full_run.md                   # 完整执行示例
```
