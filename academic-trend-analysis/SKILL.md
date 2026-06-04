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
> 以下 4 个节点**必须停止并等待用户回复**，其余全部自动执行。
> 跳过任一检查点将导致后续脚本拒绝执行（`sys.exit(1)`）。
>
> | # | 检查点 | 何时停止 | 等待什么 | 如何继续 |
> |---|--------|---------|---------|---------|
> | 1 | **Stage 0 模式选择** | 环境探测完成后 | 四合一组合选择（检索 + 对话） | 拿到选择后进入 Milvus 路径确认（如需要） |
> | 2 | **Stage 1 内部** | WebSearch 完成后 | 按对话模式展开对话（标准 5 层 / 快速 1-2 轮） | 拿到回复后构建 demand.json |
> | 3 | **Stage 1 → 2** | demand.json 生成后 | 展示内容，等用户说「继续」/「confirm」 | 用户确认后运行 `stage1_demand.py --only-confirm <data_dir>` 设置 `user_confirmed: true` |
> | 4 | **Stage 8 后** | 用户要求修订时 | 收集具体修订请求 | 重新执行 Stage 6-8（max 2 轮） |
>
> **Stage 2-8 全部自动执行**，每步完成后展示结果即可，不需等待。
> 用户可在 Stage 1 确认后说「继续执行完」，此时一次性执行 Stage 2-8。
>
> ⚠️ **如果跳过检查点直接运行 Stage 2+，脚本会输出 `🛑 GUARD BLOCKED` 并退出。**
>
> 详见 [`references/interaction-guide.md`](references/interaction-guide.md)。

端到端学术趋势分析工作流，基于多源论文搜索 + BM25 检索 + LLM 推理，
生成带有 GB/T 7714 参考文献的趋势分析报告。

**自包含设计**: 所有代码在 `lib/` 和 `scripts/` 目录中，无需外部依赖（仅需 `requests`），可在任何环境运行。

## 交互原则

> 本流程中以下节点需要**停止并等待用户确认**：
>
> | 节点 | 条件 | 动作 |
> |------|------|------|
> | Stage 0 | 环境探测完成后 | 四合一组合选择：BM25/Milvus + 标准/快速 |
> | Stage 1 内部 | WebSearch 完成 | 按对话模式展开对话（标准 5 层 / 快速 1-2 轮） |
> | Stage 1 → 2 | demand.json 生成 | 展示内容，等待"继续"确认 |
> | Stage 8 后 | 用户要求修订 | 收集修订请求，检查 revision_count（max 2） |
>
> **其余 Stage（2-8）为自动化步骤**，完成后向用户展示结果即可，不需要停止等待。
> 用户可在 Stage 1 确认后说"继续执行完"，此时一次性执行 Stage 2-8。
>
> 详见 [`references/interaction-guide.md`](references/interaction-guide.md)。

## Quick Start

```
分析 hierarchical reinforcement learning 的趋势
```

→ 首先执行 **Stage 0（环境探测 + 模式确认）**，确认本次使用 BM25 还是 Milvus 后，
再从 Stage 1 开始按阶段逐步执行，最终输出 `report.md`。

**执行方式**: 按 `agents/` 目录下的指导文件逐步编排（如工具支持 Agent 委派）；否则按 SKILL.md 内联指令执行。
Stage 0/1 含交互检查点（⛔），Stage 2-8 自动执行，每步完成后展示结果。

> ⚠️ **模式必须在 Stage 0 一次性确认**：模式写入 `demand.json.mode` 后，
> Stage 3/4/5 全部自动复用，避免中途切换导致数据/索引不一致。

---

## Pipeline Stages

| Stage | 名称 | 执行方式 | 输出 | 交互 |
|-------|------|----------|------|------|
| 0 | 环境探测 + 模式选择 |agent + `scripts/stage0_mode.py` | 终端报告 | ⛔ 四合一组合选择 |
| 1 | 需求解析 (+Socratic) |agent + `scripts/stage1_demand.py` | `demand.json`（含 `mode` + `dialogue_mode`） | ⛔ 5 层对话 → WebSearch 补充 + 确认 |
| 2 | 论文搜索 | `scripts/stage2_search.py` | `paper_pre_list.json` | 自动 → 展示结果 |
| 3 | 摘要存储 | `scripts/stage3_store.py` | `abstracts.json` | 自动 → 展示结果 |
| 4 | 核心论文筛选 | `scripts/stage4_select.py` | `core_papers.json` | 自动 → 展示结果 |
| 5 | 补充论文检索 | `scripts/stage5_supplement.py` | `supplement_papers.json` | 自动 → 展示结果 |
| 5.5 | 文献质量分级 | `scripts/stage5_5_quality_tier.py` | `quality_tiers.json` | 自动 → 展示结果 |
| 6 | 构建 Prompt | `scripts/stage6_build_prompt.py` | `report_prompt.md` | 自动 → 展示结果 |
| 7 | 撰写报告 | Agent 按 prompt 撰写 | `report_draft.md` | 自动 → 展示结果 |
| 8 | 保存报告 | `scripts/save_report.py` | `report.md` | 自动 → 展示结果 |
| — | 报告修订 | Stage 6-8 重跑 | `report.md`（修订） | ⛔ 用户要求时（max 2 轮） |

### 状态机

```
START
  │
  ▼
┌──────────────────────────────┐
│ Stage 0                      │  环境探测 → 四合一组合选择
│ Agent                        │  ⛔ 检索(BM25/Milvus) + 对话(标准/快速)
└──────┬───────────────────────┘
       │
       │  如果选择 Milvus
       ▼
┌──────────────────────────────┐
│ Milvus 路径确认              │  ⛔ 嵌入模型路径 + 数据库保存路径
│ Agent                        │  确认或用户提供
└──────┬───────────────────────┘
       ▼
┌──────────────────────────────┐
│ Stage 1                      │  ⛔ 对话(标准 5 层 / 快速 1-2 轮) → WebSearch
│ Agent                        │  → 缺口分析 → demand.json → ⛔ 用户确认
└──────┬───────────────────────┘
       ▼
┌─────────────┐
│ Stage 2-8   │  自动执行（搜索→存储→筛选→补充→分级
│ auto        │  →Prompt→撰写→保存），每步完成后展示结果
└──────┬──────┘
       ▼
┌──────────────────┐  用户要求修订？
│ 报告修订（可选）  │  Yes → Stage 6-8 重跑（max 2 轮）
│ on demand        │  No  → DONE
└──────┬───────────┘
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

按以下步骤逐步执行：

### Stage 0: 环境探测 + 模式确认（**必须前置**）

```bash
python academic-trend-analysis/scripts/stage0_mode.py            # 人类可读报告
python academic-trend-analysis/scripts/stage0_mode.py --json     # JSON 结构（程序化）
python academic-trend-analysis/scripts/stage0_mode.py --base_dir /path/to/project  # 指定数据存放根目录
```

> `--base_dir` 默认为当前工作目录（即 `pwd`），所有数据将存放在 `<base_dir>/data/<timestamp>/` 下。
> 也可直接传入 `--data_dir /完整/路径` 指定完整数据目录。

输出包含：
- 当前环境是否安装 `pymilvus` / `sentence-transformers`
- 是否检测到本地 Milvus 数据库及已有 collection
- 推荐检索模式（基于环境）

将报告展示给用户，并展示 **四合一组合选择**：
```
1. BM25 + 标准模式（5 层对话）     2. BM25 + 快速模式（1-2 轮澄清）
3. Milvus + 标准模式              4. Milvus + 快速模式
```

⛔ **STOP**：等待用户选择组合模式后再进入 Stage 1。
如果只有一种检索模式可用，自动选择该检索模式，仅展示对话模式（标准/快速）二选一。

**确认后的模式**：
- 检索模式作为 `--mode` 传入 Stage 1，写入 `demand.json.mode`
- 对话模式作为 `--dialogue_mode` 传入 Stage 1，写入 `demand.json.dialogue_mode`

**Milvus 路径确认**（仅 Milvus 模式）：

如果用户选择了 Milvus 检索模式，必须确认两个路径：
1. **嵌入模型路径**：检查环境变量 `MILVUS_EMBEDDING_MODEL`，若无则询问用户
2. **数据库保存路径**：检查环境变量 `MILVUS_DATA_PATH`，若无则询问用户

两个路径将写入 `demand.json` 的 `embedding_model_path` 和 `milvus_data_path` 字段。
BM25 模式下跳过此步骤。

### Stage 1: 需求解析

**必须**先执行以下步骤，再运行脚本：

1. **读取 `demand.json.dialogue_mode`**，决定对话模式：
   - **标准模式**（`dialogue_mode = socratic`）：按 5 层苏格拉底框架引导用户澄清
     - Layer 1: 范围界定 → Layer 2: 维度选择 → Layer 3: 证据标准
     - Layer 4: 偏差意识 → Layer 5: 贡献阐述
     - 收敛信号 3+ = 收敛，进入下一步
     - 详见 [`agents/demand_analyzer.md`](agents/demand_analyzer.md) `## Socratic Dialogue`
   - **快速模式**（`dialogue_mode = quick`）：跳过 5 层对话，仅 1-2 轮 WebSearch 澄清

2. ⛔ **STOP**：向用户提出澄清问题（标准模式按 5 层展开，快速模式 1-2 轮），**等待回复**

3. 基于用户回复构造初步 `query_terms` 和 `dialogue_summary`（标准模式）

4. **WebSearch** 搜索 `"{query} research trends latest advances 2025 2026"`，针对对话中明确的缺口做补充调研
   - 如果搜索失败（≥3 次），向用户报告并请求手动提供领域背景信息

5. 基于搜索结果 + 用户回复构造最终 `query_terms` 和 `web_summary`
   - 标准模式收敛后，生成 `dialogue_summary` 对象

然后传入脚本：

```bash
python academic-trend-analysis/scripts/stage1_demand.py "研究方向关键词" [data_dir] \
    --mode <bm25|milvus> \
    --dialogue_mode <socratic|quick> \
    --query_terms "term1" "term2" "term3" \
    --web_summary "基于网络搜索的领域背景摘要，2-4 句"
```

> ⚠️ `--query_terms` 和 `--web_summary` 应来自真实调研。
> 若省略，脚本会 fallback 到内置模板，但输出 ⚠️ 质量警告。

生成 `demand.json`，包含扩展关键词、时间范围、领域背景摘要、**mode 字段**、**dialogue_mode 字段**。
标准模式下还会写入 `dialogue_summary`。

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

展示分级报告给用户，若 T2+T3 占比过高（>60%），须在报告中加入质量声明。

### Stage 6: 构建 Prompt（自动执行 → 完成后展示结果）

```bash
python academic-trend-analysis/scripts/stage6_build_prompt.py <data_dir>
```

合并核心论文摘要和补充论文元数据，构建报告生成 Prompt。

### Stage 7: 撰写报告（自动执行 → 完成后展示结果）

读取 `report_prompt.md`，**严格按照其中的模板结构**撰写趋势分析报告，保存为 `report_draft.md`。

**撰写质量要求**：
- **严格遵循模板结构**：按模板中的 8 个章节（领域概览 → 研究方向与分类 → 代表性论文 → 技术趋势 → 热门方向 → 应用前景 → 未来展望 → 现存挑战）逐一撰写，不可省略任何章节
- **详细分析，非摘要**：每个子方向须包含分类标准说明、核心挑战、关键进展（含具体论文标题、作者、年份、核心贡献），不可仅列标题或一句话总结
- **引用必须具体**：提及观点/方法/数据时须用 `[N]` 引用，引用须附带具体论文信息（作者、年份、关键数据如成功率/PSNR/论文数量等）
- **表格完整填充**：代表性论文一览和技术演进路线表格须完整填充，每格含具体论文和数据
- **报告长度**：正文（不含参考文献）应在 **200 行以上**，每个主要章节不少于 3 段
- **标注推断**：跨论文推测、未来预测、未验证假设须标注 `[推断]`
- **负趋势必须包含**：至少指出一个停滞/衰退方向及长期未解决的问题

完成后向用户展示报告路径、行数、引用数量和概要。

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

data_dir = Path("data/2026-06-04-15-31-hierarchical-reinforcement")  # 时间+主题

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
data/YYYY-MM-DD-HH-MM-主题/
├── demand.json              # 结构化需求（含 mode + dialogue_mode + dialogue_summary）
│                            # Milvus 模式下含 embedding_model_path + milvus_data_path
├── paper_pre_list.json      # 搜索结果（去重后）
├── abstracts.json           # 摘要存储
├── core_papers.json         # 核心论文（含 BM25 score）
├── quality_tiers.json       # 文献质量分级报告
├── supplement_papers.json   # 补充论文（含 RRF score）
├── report_prompt.md         # 报告生成 Prompt
├── report_draft.md          # 报告草稿（Agent 撰写）
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
| LLM | Agent 直接撰写 | Agent 直接撰写 |

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
6. **对话模式**：Stage 0 用户选择标准/快速模式。标准模式启动 5 层苏格拉底对话；快速模式仅 1-2 轮澄清。模式写入 `demand.json.dialogue_mode`
7. **Milvus 路径确认**：选择 Milvus 模式时，必须确认嵌入模型路径和数据库保存路径（环境变量优先，无则询问用户）。写入 `demand.json.embedding_model_path` 和 `demand.json.milvus_data_path`
8. **报告迭代**：Stage 8 完成后用户可要求修订。收集修改意见，重跑 Stage 6-8（max 2 轮）。`demand.json.revision_count` 跟踪修订次数

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
│   ├── demand_analyzer.py            # 需求分析逻辑（含苏格拉底对话辅助）
│   ├── paper_search.py               # 多源搜索 + 去重 + 关键词扩展
│   ├── paper_retrieval.py            # BM25/Milvus 检索 + 摘要存储
│   └── report_builder.py             # Prompt 构建 + 报告保存
├── scripts/
│   ├── stage0_mode.py                # Stage 0: 环境探测 + 模式推荐
│   ├── _mode_resolver.py             # 共享：mode 解析（CLI > demand.json > default）
│   ├── _guard.py                     # 共享：检查点守卫（校验 Stage 顺序与 user_confirmed）
│   ├── stage1_demand.py              # Stage 1: 需求解析（写入 mode）
│   ├── stage2_search.py              # Stage 2: 论文搜索 + 去重
│   ├── stage3_store.py               # Stage 3: 摘要入库（自动读 mode）
│   ├── stage4_select.py              # Stage 4: 核心论文筛选（自动读 mode）
│   ├── stage5_supplement.py          # Stage 5: 补充论文 RRF 检索（自动读 mode）
│   ├── stage5_5_quality_tier.py      # Stage 5.5: 文献质量分级（T1/T2/T3）
│   ├── stage6_build_prompt.py        # Stage 6: 构建报告 Prompt
│   └── save_report.py                # Stage 8: 保存报告（含参考文献）
├── references/
│   ├── workflow.md                   # 阶段详细定义
│   ├── rag-architecture.md           # 技术架构说明
│   ├── interaction-guide.md          # 交互检查点指南
│   └── gap_analysis_guide.md         # 缺口分析指南（Stage 1 关键词生成前）
├── templates/
│   └── report_template.md            # 报告生成模板（8 段式结构）
└── examples/
    └── full_run.md                   # 完整执行示例
```
