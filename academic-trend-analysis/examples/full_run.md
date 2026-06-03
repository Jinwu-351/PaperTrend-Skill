# 完整执行示例

## 场景：分析 hierarchical reinforcement learning 的趋势

### 前置条件

```bash
# BM25 模式：仅需 requests
pip install requests

# Milvus 模式：额外需要
pip install pymilvus sentence-transformers
```

### Stage 0: 环境探测 + 模式确认（**必须前置**）

```bash
python academic-trend-analysis/scripts/stage0_mode.py
```

输出示例：

```
============================================================
Stage 0: 环境探测 & 模式推荐
============================================================

[环境检测]
  pymilvus              : ✓
  sentence-transformers : ✓
  Milvus DB 路径        : milvus_data/milvus_data.db
  Milvus DB 存在        : ✓

[可用模式]
  [✓] bm25    — 零依赖，关键词 BM25 匹配，毫秒级
  [✓] milvus  — 向量语义检索 (BGE embedding + 余弦相似度)，检测到已有 collection: ['paper_knowledge_base']
        已有 collections: ['paper_knowledge_base']

💡 推荐模式: milvus
```

Claude Code 把报告展示给用户，等用户确认（例如选择 `milvus`）后再进入 Stage 1。

### Stage 1: 需求解析（含 WebSearch 调研结果）

Claude Code 先用 WebSearch 搜索该领域最新趋势，然后向用户提问澄清，最后调用：

```bash
python academic-trend-analysis/scripts/stage1_demand.py "hierarchical reinforcement learning" \
    --mode milvus \
    --query_terms "hierarchical reinforcement learning" "HRL" "option framework" "temporal abstraction" "skill discovery" \
    --web_summary "HRL 是强化学习的重要分支，通过将复杂任务分解为多个层级的子策略来提高学习效率。近年来在 LLM 规划、机器人控制等领域有广泛应用。"
```

输出：

```
Stage 1 完成: data/2026-05-27-15-31/demand.json
  查询: hierarchical reinforcement learning
  扩展词 (5): ['hierarchical reinforcement learning', 'HRL', 'option framework', 'temporal abstraction', 'skill discovery']
  模式: milvus  (后续 Stage 3/4/5 将默认使用该模式)
  时间范围: 2024-05-27 至 2026-05-27
  web_summary 长度: 92 字符
```

### Stage 2: 论文搜索

```bash
python academic-trend-analysis/scripts/stage2_search.py data/2026-05-27-15-31
```

输出：

```
Stage 2: 论文搜索
  关键词: ['hierarchical reinforcement learning', 'HRL', 'deep reinforcement learning', 'DRL', 'policy gradient']
  每源最大: 25
  时间范围: 2024-2026

=== [1/5] 搜索: hierarchical reinforcement learning ===
  arXiv: 25 篇
  Semantic Scholar: 18 篇
  OpenAlex: 22 篇
  AlphaXiv: 8 篇
  ...

Stage 2 完成: data/2026-05-27-15-31/paper_pre_list.json
  搜索总计: 156 篇
  去重后: 89 篇
```

### Stage 3: 摘要存储

```bash
python academic-trend-analysis/scripts/stage3_store.py data/2026-05-27-15-31
```

> 无需再传 `--mode`：脚本自动从 `demand.json.mode` 读取。

输出：

```
[mode resolution] source=demand.json value=milvus
Stage 3: 摘要入库 (mode=milvus)
  待入库论文: 89 篇
  Milvus 入库: 新增 89 篇，跳过 0 篇
  Milvus 总计: 89 篇

Stage 3 完成: data/2026-05-27-15-31/abstracts.json
```

### Stage 4: 核心论文筛选

```bash
python academic-trend-analysis/scripts/stage4_select.py data/2026-05-27-15-31
```

输出：

```
Stage 4: 核心论文筛选 (query='hierarchical reinforcement learning', limit=6)

Stage 4 完成: data/2026-05-27-15-31/core_papers.json
  [1] score=12.34  Hierarchical Reinforcement Learning...
  [2] score=11.87  Option-Critic Architecture...
  ...
```

### Stage 5: 补充论文检索

```bash
python academic-trend-analysis/scripts/stage5_supplement.py data/2026-05-27-15-31
```

输出：

```
Stage 5: 补充论文 RRF 检索 (terms=5, top_k=40)

Stage 5 完成: data/2026-05-27-15-31/supplement_papers.json
  补充论文: 40 篇
```

### Stage 6: 构建 Prompt

```bash
python academic-trend-analysis/scripts/stage6_build_prompt.py data/2026-05-27-15-31
```

输出：

```
Stage 6: 构建报告 Prompt
  查询: hierarchical reinforcement learning
  论文总数: 46 (核心 6 + 补充 40)

Stage 6 完成: data/2026-05-27-15-31/report_prompt.md
  Prompt 长度: 15234 字符

下一步: 根据 prompt 撰写趋势分析报告，保存为 report_draft.md
  然后运行: python scripts/save_report.py data/2026-05-27-15-31 <report_draft.md>
```

### Stage 7: 撰写报告

Claude Code 阅读 `report_prompt.md`，撰写趋势报告，保存为 `report_draft.md`。

### Stage 8: 保存最终报告

```bash
python academic-trend-analysis/scripts/save_report.py data/2026-05-27-15-31 data/2026-05-27-15-31/report_draft.md
```

输出：

```
已提取 23 个引用，映射为连续编号
已生成 23 条 GB/T 7714 参考文献
报告已保存: data/2026-05-27-15-31/report.md
```

### 最终文件结构

```
data/2026-05-27-15-31/
├── demand.json              # 结构化需求
├── paper_pre_list.json      # 89 篇搜索结果
├── abstracts.json           # 89 篇摘要
├── core_papers.json         # 6 篇核心论文
├── supplement_papers.json   # 40 篇补充论文
├── report_prompt.md         # 报告生成 Prompt
├── report_draft.md          # 报告草稿
└── report.md                # 最终报告（含参考文献）
```
