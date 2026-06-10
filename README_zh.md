# Academic Trend Analysis

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> AI Agent 驱动的学术论文趋势分析 Skill。一句话启动调研，自动完成搜索、筛选、分析、报告生成全流程。

[English](README.md) | 简体中文

---

## 项目背景

在科研工作中，文献调研是最耗时却又最不可或缺的环节：

- **查不全**：单一数据库覆盖有限，容易遗漏重要工作
- **去重烦**：同一篇论文在不同平台反复出现，手动去重效率低下
- **筛选难**：从数百篇论文中找出核心文献，需要大量阅读与判断
- **格式乱**：引用格式不统一，整理参考文献消耗大量时间
- **洞察浅**：缺乏系统性分析框架，难以提炼真正的趋势与缺口

本项目将上述流程打包为一个 **AI Agent Skill**。你只需用自然语言描述研究方向，Agent 会自动完成从需求澄清、多源搜索、去重筛选、质量分级到报告撰写的全部工作，最终输出一份带 GB/T 7714 参考文献的学术趋势分析报告。

---

## 核心优势

| 传统方式 | Academic Trend Analysis |
|---------|------------------------|
| 手动逐个数据库检索 | 一次搜索覆盖 arXiv、Semantic Scholar、OpenAlex、AlphaXiv 四源 |
| 人工比对去重 | 自动 DOI + 标题归一化 + arXiv ID 三重去重 |
| 凭经验筛选核心文献 | BM25 相关性排序 + 标题匹配加权，客观量化 |
| 难以判断文献质量 | 自动 T1/T2/T3 三级质量标注，预印本与顶会一目了然 |
| 参考文献格式混乱 | 自动提取引用、重映射连续编号、追加 GB/T 7714 标准格式 |
| 报告结构凭感觉 | 8 段式标准模板：背景→方法聚类→核心成果→负趋势→未来方向→结论 |

**关键设计**：

- **零配置即可用**：默认 BM25 模式仅需 `requests`，无需 GPU、无需向量数据库
- **人在回路**：仅在模式选择、需求确认阶段暂停提问，确认后一次性自动跑完全流程
- **自包含可审计**：每步中间结果（搜索列表、核心论文、质量分级）均持久化到本地，随时可追溯
- **缺口分析驱动**：关键词生成前强制检查领域主流方向覆盖度，避免调研盲区
- **苏格拉底对话**：标准模式下通过 5 层深度对话（范围界定→维度选择→证据标准→偏差意识→贡献阐述）精准定位分析需求

---

## 适用场景

### 1. 研究方向入门

刚接触一个新领域，需要快速建立全局认知：

> "帮我调研一下 **NeRF 在自动驾驶中的应用** 现状"

Agent 会自动搜索最新论文，筛选核心工作，生成一份涵盖方法演进、关键成果、现存问题与前景的综述报告。

### 2. 项目上下文驱动的趋势分析

在项目目录下使用 AI Agent 时，Agent 已经理解了你的代码结构、依赖栈和技术选型。此时触发本 Skill，调研方向会与项目实际紧密贴合：

> "我们项目里用了自研的分布式训练框架，**帮我看看最近分布式深度学习训练** 有什么新进展，有没有值得借鉴的"

Agent 会结合它已读到的项目代码（如 `train.py` 中的数据并行逻辑、`model.py` 的架构设计），在报告中标注：
- 哪些新方法是项目**已经采用**的（现状对齐）
- 哪些是**可以考虑升级**的（技术债务预警）
- 哪些是**目前项目未涉及但相关**的（扩展机会）

这比"盲搜"一个研究方向要精准得多，因为分析锚点是你的真实代码基线。

### 3. 开题前的文献综述

撰写学位论文或项目申请书前，需要系统性梳理领域脉络：

> "分析 **扩散模型在医学图像分割** 方向的研究趋势，重点关注近两年的工作"

输出报告可直接作为文献综述章节的基础框架，引用格式已按 GB/T 7714 整理好。

### 4. 技术选型对比

面对多个技术路线，需要了解各自的发展态势与边界：

> "对比一下 **Mamba 和 Transformer 在长序列建模** 上的最新进展，各有什么优势和局限"

Agent 会分别搜索两个方向的代表性工作，在报告中进行结构化对比分析。

### 5. 组会前的速览

下周要汇报，需要快速掌握一个子方向的动态：

> "最近 **大模型推理时扩展（test-time scaling）** 有什么新进展？"

30 分钟内获得一份带引用的精炼摘要，足以支撑一次高质量的组会分享。

### 6. 审稿准备

收到一篇论文的审稿邀请，需要了解相关工作背景：

> "帮我查一下 **基于图神经网络的药物发现** 领域的关键论文，看看最近有没有突破性工作"

快速定位领域内的里程碑工作与最新进展，辅助审稿判断。

### 7. 跨学科交叉探索

寻找本领域与其他学科的交叉机会：

> "看看 **强化学习在芯片设计（EDA）** 上的应用现状"

通过缺口分析自动识别该交叉领域的主流方向与未被覆盖的细分主题。

### 8. 基金/项目申报

需要论证某研究方向的前沿性与必要性：

> "调研 **具身智能（embodied AI）在家庭服务机器人** 方向的研究动态，重点分析还有哪些技术瓶颈未解决"

报告中的"负趋势分析"与"未来方向"段落可直接用于项目书的研究意义与难点阐述。

---

## 部署方式

本 Skill 支持 **Claude Code + Codex 双工具部署**。两个工具的 Skill 目录结构完全兼容，一份代码、一个入口。

Claude Code 和 Codex 从以下位置加载 Skill：

- **全局 Skills**：`~/.claude/skills/` 或 `~/.codex/skills/` — 任何项目都能触发
- **项目 Skills**：`<project>/.claude/skills/` 或 `<project>/.codex/skills/` — 仅在该项目内可用

### 一键部署（推荐）

使用仓库根目录的 `deploy.py` 跨平台一键部署：

```bash
# 全局部署（两个工具都可用）
python deploy.py --global

# 仅项目级部署
python deploy.py --local

# 预览操作，不实际执行
python deploy.py --dry-run --global

# 卸载
python deploy.py --remove
```

平台自动适配：Linux/macOS 使用符号链接，Windows 使用目录连接（`mklink /J`）。

Codex 部署优先读取 `$CODEX_HOME` 环境变量，未设置时 fallback 到 `~/.codex/skills/`。

### 手动部署

如需手动复制，将 `academic-trend-analysis/` 目录分别复制到目标位置：

```bash
# 全局部署
cp -r academic-trend-analysis ~/.claude/skills/
cp -r academic-trend-analysis ~/.codex/skills/

# 项目级部署
mkdir -p .claude/skills .codex/skills
cp -r academic-trend-analysis .claude/skills/
cp -r academic-trend-analysis .codex/skills/

# 验证
ls ~/.claude/skills/academic-trend-analysis/SKILL.md
ls ~/.codex/skills/academic-trend-analysis/SKILL.md
```

> **区别**：全局部署一次，所有项目通用；项目部署仅对当前项目生效。一键部署使用符号链接/目录连接，源码修改即时生效，无需重复部署。

---

## 使用方式

### 自然语言触发

无需记忆命令，直接用日常语言描述需求：

```
分析 X 的趋势
X 领域的论文调研
X 方向的研究动态
帮我搜索 X 相关的论文并生成综述
```

触发词包括：趋势、前沿、热点、论文调研、文献综述、research trend、academic survey、paper search、领域分析、research landscape、literature review。

### 交互流程

整个流程分为 **5 个人工确认点 + 全自动阶段**：

```
你: "分析 hierarchical reinforcement learning 的趋势"
    │
    ▼
┌─────────────────────────────────────┐
│ Stage 0: 环境探测 + 模式选择          │
│ Agent 检测 BM25 / Milvus 可用性      │
│ ⛔ 展示四合一组合选择，等待你确认      │
│   BM25/Milvus × 标准/快速            │
└─────────────────┬───────────────────┘
                  ▼
           选择 Milvus？
┌─────────────────┬───────────────────┐
│ 是              │ 否                │
│ ⛔ 确认嵌入模型  │                   │
│    和数据路径    │                   │
└────────┬────────┘                   │
         ▼                            ▼
┌─────────────────────────────────────┐
│ Stage 1: 需求解析                    │
│ 标准模式 → 5 层苏格拉底对话           │
│ 快速模式 → 1-2 轮澄清               │
│ Agent 网络搜索 → 展开对话/提问       │
│ ⛔ 生成 demand.json，等你确认"继续"   │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ Stage 2-8: 全自动执行                │
│ 搜索 → 存储 → 筛选 → 补充 → 分级     │
│ → Prompt → 撰写 → 保存              │
│ 每步完成后展示结果，无需等待          │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ 报告完成后                           │
│ ⛔ 你可要求修订（max 2 轮）           │
└─────────────────┬───────────────────┘
                  ▼
           输出 report.md
```

你可以随时说"继续执行完"，让 Agent 一次性跑完剩余阶段。

---

## 技术 Pipeline

后端自动执行的 8 个阶段 + 可选修订循环：

| Stage | 动作 | 输出 | 交互 |
|-------|------|------|------|
| 0 | 环境探测 + 模式选择 | 四合一组合选择 | ⛔ 检索模式(BM25/Milvus) + 对话模式(标准/快速) |
| — | Milvus 路径确认（仅 Milvus） | 嵌入模型 + 数据路径 | ⛔ 确认环境变量或询问用户 |
| 1 | 需求解析（标准模式 5 层对话 / 快速 1-2 轮 + 缺口分析） | `demand.json` | ⛔ 需求确认 |
| 2 | 四源论文搜索（arXiv / Semantic Scholar / OpenAlex / AlphaXiv） | `paper_pre_list.json` | 自动 |
| 3 | 摘要存储（BM25 JSON 或 Milvus 向量入库） | `abstracts.json` | 自动 |
| 4 | 核心论文筛选（BM25 相关性 + 标题加权） | `core_papers.json` | 自动 |
| 5 | 补充论文检索（多关键词 RRF 融合） | `supplement_papers.json` | 自动 |
| 5.5 | 文献质量分级（T1 顶会 / T2 预印本 / T3 待核实） | `quality_tiers.json` | 自动 |
| 6 | 构建报告 Prompt | `report_prompt.md` | 自动 |
| 7 | Agent 按模板撰写报告 | `report_draft.md` | 自动 |
| 8 | 提取引用 + 重映射编号 + GB/T 7714 参考文献 | `report.md` | 自动 |
| — | 报告修订（用户触发，max 2 轮） | `report.md`（修订） | ⛔ 收集修改意见 → 重跑 Stage 6-8 |

所有中间产物保存在 `data/YYYY-MM-DD-HH-MM-主题/` 目录下（如 `data/2026-06-04-12-00-hierarchical-reinforcement/`），每次运行自动隔离，方便回溯和对比。

---

## 两种检索模式 + 两种对话模式

### 检索模式

| 模式 | 依赖 | 特点 | 适用场景 |
|------|------|------|---------|
| **BM25**（默认） | `requests` | 零配置、毫秒级、基于关键词匹配 | 快速验证、首次使用、无 GPU 环境 |
| **Milvus** | `pymilvus` + `sentence-transformers` | 语义召回、BGE 向量相似度 | 追求最高检索质量、有本地向量库 |

> BM25 对学术论文摘要的检索效果与轻量向量检索相当，推荐默认使用。仅在需要深度语义召回时切换到 Milvus。

### 对话模式

| 模式 | 交互深度 | 特点 | 适用场景 |
|------|---------|------|---------|
| **标准模式** | 5 层苏格拉底对话 | 范围界定 → 维度选择 → 证据标准 → 偏差意识 → 贡献阐述 | 需求模糊、希望深度澄清 |
| **快速模式** | 1-2 轮快速澄清 | 直接 WebSearch + 简洁提问 | 已有明确分析目标 |

> Stage 0 中两个模式组合为四选一：`BM25+标准`、`BM25+快速`、`Milvus+标准`、`Milvus+快速`。

### Milvus 模式额外配置

选择 Milvus 模式时，需确认以下两项：

1. **嵌入模型路径**：优先读取环境变量 `MILVUS_EMBEDDING_MODEL`，未设置时由 Agent 询问你提供
2. **数据库保存路径**：优先读取环境变量 `MILVUS_DATA_PATH`，未设置时由 Agent 询问你提供

两个路径会写入 `demand.json`，后续 Stage 自动读取，无需重复指定。

推荐模型： [BAAI/bge-large-zh-v1.5](https://huggingface.co/BAAI/bge-large-zh-v1.5)（1024 维）。

> **Windows 用户注意**：如果 `python` 或 `pip` 不在 PATH 中，请使用 `python -m pip install ...` 或在 Anaconda/Miniconda 环境中安装。本 Skill 开发环境为 `conda activate agno`，但不强制依赖 conda。

---

## 项目结构

```
academic-trend-analysis/
├── SKILL.md                    # Skill 定义与完整使用文档
├── agents/                     # Agent 指令
│   ├── mode_selector.md        # 模式选择器（Stage 0，四合一组合选择）
│   ├── demand_analyzer.md      # 需求分析师（Stage 1，含 5 层苏格拉底对话）
│   ├── paper_searcher.md       # 论文搜索员（Stage 2）
│   ├── knowledge_manager.md    # 知识管理员（Stage 3-5）
│   └── trend_reporter.md       # 趋势报告员（Stage 6-8 + 报告修订）
├── lib/                        # 自包含代码库
│   ├── paper_search.py         # 多源搜索 + 去重 + 关键词扩展
│   ├── paper_retrieval.py      # BM25/Milvus 检索 + 摘要存储
│   └── report_builder.py       # Prompt 构建 + 报告保存
├── scripts/                    # Stage 0-8 可执行脚本（由 Agent 自动调用）
├── references/                 # 流程参考文档
├── templates/                  # 报告生成模板
└── examples/                   # 完整执行示例
```

---

## 依赖

Python 3.10+ 环境。依赖按模式分离，按需安装：

### BM25 模式（默认，零配置）

仅需 `requests`，使用关键词 BM25 匹配，适合大多数场景：

```bash
pip install -r academic-trend-analysis/requirements.txt
# 或单独安装: pip install requests
```

### Milvus 向量检索模式（可选）

需要额外的向量检索依赖，适合追求深度语义召回的场景：

```bash
pip install pymilvus sentence-transformers
```

**嵌入模型路径**和**数据库保存路径**：
选择 Milvus 模式时，Agent 会在 Stage 0 引导你确认：
- 优先读取环境变量 `MILVUS_EMBEDDING_MODEL` / `MILVUS_DATA_PATH`
- 未设置时，Agent 会交互式询问你提供路径
- 确认后路径写入 `demand.json`，后续 Stage 自动读取

也可通过环境变量预设：

```bash
# Linux / macOS
export MILVUS_EMBEDDING_MODEL=/path/to/bge-large-zh-v1.5
export MILVUS_DATA_PATH=./milvus_data

# Windows
set MILVUS_EMBEDDING_MODEL=C:\models\bge-large-zh-v1.5
set MILVUS_DATA_PATH=C:\milvus_data
```

推荐模型：[BAAI/bge-large-zh-v1.5](https://huggingface.co/BAAI/bge-large-zh-v1.5)（1024 维）

---

## License

MIT
