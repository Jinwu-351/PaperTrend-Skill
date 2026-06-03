# 技术架构说明

## 检索引擎架构

本 skill 提供两种检索后端，用户可在运行时选择：

### 模式 A：BM25 关键词检索（默认，零依赖）

```
论文摘要 → 中英文分词 → BM25 索引 → 关键词检索 / RRF 融合
```

- **实现**：`lib/paper_retrieval.py` — `AbstractStore` + `BM25Retriever`
- **依赖**：Python 标准库（`json`, `re`, `math`, `collections`）
- **优点**：零配置、启动快（<1s）、可移植
- **缺点**：仅关键词匹配，无法语义召回

### 模式 B：Milvus 向量检索 + BGE embedding

```
论文摘要 → BGE embedding → Milvus 向量入库 → 余弦相似度检索 / RRF 融合
```

- **实现**：`lib/paper_retrieval.py` — `MilvusStore`
- **依赖**：`pymilvus`, `sentence-transformers`, embedding 模型
- **优点**：语义召回、支持同义但关键词不匹配的论文
- **缺点**：需要 embedding 模型（~1.2GB）、启动慢（10-30s）、依赖 Milvus

### 统一接口

两种模式共享相同的接口，下游代码（核心论文筛选、补充检索、报告构建）无需修改：

```python
# 两种模式统一接口
store.add_batch(papers)     # 摘要入库
store.save()                 # 持久化
store.all_papers()           # 获取所有论文
store.count()                # 论文总数

# 核心论文筛选（内部使用各自的检索引擎）
from paper_retrieval import select_key_papers
core = select_key_papers(store, query, limit=6)

# 补充检索
retriever = store.get_retriever()
supplement = retriever.search_multi_rrf(queries, top_k=40, exclude_titles=...)
```

### 选择建议

| 场景 | 推荐模式 |
|------|---------|
| 首次使用 / 快速验证 | BM25 |
| 需要语义召回（同义词、跨语言表达） | Milvus |
| 无 embedding 模型可用 | BM25 |
| 追求最高检索质量 | Milvus |

### 模式决策树（Stage 0 用）

```
开始
 │
 ├─ pymilvus 未安装？ ──── 是 ──► 强制 BM25
 │           │
 │          否
 │           │
 ├─ 检测到已有 milvus_data.db collection？ ── 是 ──► 推荐 Milvus（可复用历史向量）
 │           │
 │          否
 │           │
 ├─ 用户表明只是快速验证 / 不到 200 篇？ ── 是 ──► 推荐 BM25
 │           │
 │          否
 │           │
 └─► 推荐 Milvus（语义检索质量更高）
```

> Stage 0 (`scripts/stage0_mode.py`) 会综合输出 `available` / `recommended`，
> Claude 必须把推荐结果展示给用户，等待用户最终确认后再写入 `demand.json.mode`。

### 模式贯穿全流程

| Stage | 是否读 mode | 来源 |
|-------|-------------|------|
| Stage 0 | 输出 mode 推荐 | 环境探测 |
| Stage 1 | 写入 `demand.json.mode` | CLI `--mode` |
| Stage 2 | 不读 | — |
| Stage 3 | 读 | `_mode_resolver`: CLI > demand.json > "bm25" |
| Stage 4 | 读 | 同上 |
| Stage 5 | 读 | 同上 |
| Stage 6+ | 不读 | — |

## 搜索来源

| 来源 | API | 协议 | 限制 |
|------|-----|------|------|
| arXiv | export.arxiv.org/api/query | XML | 免费，需 3s 间隔 |
| Semantic Scholar | api.semanticscholar.org/graph/v1 | REST JSON | 100 req/5min |
| OpenAlex | api.openalex.org/works | REST JSON | 免费 |
| AlphaXiv | api.alphaxiv.org/search/v2 | REST JSON + HTML 抓取 | 免费 |

## 去重策略

1. **DOI 匹配** — 同一 DOI 视为同一篇
2. **标题归一化** — 去标点、转小写、去空格差异
3. **arXiv ID 匹配** — 同一 arXiv ID 视为同一篇
4. 冲突时保留信息更完整的版本（优先有 venue 的、作者更多的）

## 报告生成

1. **Prompt 构建**：`lib/report_builder.py` — `build_trend_prompt()`
2. **报告撰写**：Claude Code 根据 prompt 撰写
3. **参考文献**：`save_report()` 自动提取 `[N]` 引用，重映射为连续编号，生成 GB/T 7714 格式
