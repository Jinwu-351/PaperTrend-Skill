# PaperTrend-Skill

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> An AI Agent-powered Skill for academic paper trend analysis. Start a research survey with a single sentence — the Agent automatically handles search, filtering, analysis, and report generation end-to-end.

English | [简体中文](README_zh.md)

---

## Background

In academic research, literature review is one of the most time-consuming yet indispensable steps:

- **Incomplete coverage**: A single database has limited coverage, making it easy to miss important work
- **Tedious deduplication**: The same paper appears repeatedly across platforms, and manual deduplication is inefficient
- **Difficult filtering**: Identifying core papers from hundreds of results requires extensive reading and judgment
- **Inconsistent formatting**: Citation formats vary widely, and organizing references consumes significant time
- **Superficial insights**: Without a systematic analysis framework, it's hard to extract real trends and research gaps

This project packages the entire workflow into an **AI Agent Skill**. Simply describe your research direction in natural language, and the Agent will handle everything from requirement clarification, multi-source search, deduplication, quality grading, to report writing — ultimately producing an academic trend analysis report with GB/T 7714 formatted references.

---

## Key Advantages

| Traditional Approach                      | Academic Trend Analysis                                                                                                       |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Manual search across databases one by one | Single search covering four sources: arXiv, Semantic Scholar, OpenAlex, AlphaXiv                                              |
| Manual comparison for deduplication       | Automatic triple deduplication via DOI + title normalization + arXiv ID                                                       |
| Experience-based core paper selection     | BM25 relevance ranking + title-match weighting for objective quantification                                                   |
| Hard to judge paper quality               | Automatic T1/T2/T3 three-tier quality labeling — preprints and top conferences at a glance                                    |
| Messy reference formatting                | Automatic citation extraction, sequential re-numbering, and GB/T 7714 standard formatting                                     |
| Report structure by intuition             | 8-section standard template: Background → Method Clustering → Core Results → Negative Trends → Future Directions → Conclusion |

**Key Design Principles**:

- **Zero-config ready**: Default BM25 mode requires only `requests` — no GPU, no vector database needed
- **Human-in-the-loop**: Pauses only for mode selection and requirement confirmation; runs the rest automatically in one shot
- **Self-contained & auditable**: Every intermediate result (search lists, core papers, quality tiers) is persisted locally and fully traceable
- **Gap-analysis driven**: Before generating keywords, the system强制 checks coverage of mainstream directions in the field to avoid blind spots
- **Socratic dialogue**: In standard mode, 5-layer deep dialogue (scope → dimensions → evidence standards → bias awareness → contribution articulation) precisely pinpoints analysis needs

---

## Use Cases

### 1. Getting Started with a New Research Direction

New to a field and need to quickly build a global understanding:

> "Help me survey the current state of **NeRF applications in autonomous driving**."

The Agent automatically searches for the latest papers, filters core works, and generates a comprehensive report covering method evolution, key results, open problems, and future prospects.

### 2. Project Context-Driven Trend Analysis

When using an AI Agent within your project directory, it already understands your code structure, dependency stack, and technology choices. Triggering this Skill aligns the research direction closely with your actual project:

> "Our project uses a custom distributed training framework. **Help me check recent advances in distributed deep learning training** — anything worth借鉴ing."

The Agent combines the project code it has already read (e.g., data parallelism logic in `train.py`, architecture design in `model.py`) and annotates in the report:
- Which new methods your project **already adopts** (alignment check)
- Which are **worth upgrading to** (technical debt warning)
- Which are **not yet covered but relevant** (expansion opportunities)

This is far more precise than "blind searching" a research direction, because the analysis anchors on your real codebase.

### 3. Literature Review Before Thesis Proposal

Before writing a thesis or grant proposal, you need a systematic review of the field:

> "Analyze research trends in **diffusion models for medical image segmentation**, focusing on work from the past two years."

The output report can serve directly as a foundational framework for your literature review chapter, with citations already formatted in GB/T 7714.

### 4. Technology Comparison

Facing multiple technical routes and need to understand each one's trajectory and boundaries:

> "Compare the latest advances of **Mamba vs. Transformer in long-sequence modeling** — what are the strengths and limitations of each?"

The Agent searches representative work in both directions and provides a structured comparative analysis in the report.

### 5. Quick Preview Before Group Meeting

Presenting next week and need to quickly catch up on a sub-direction:

> "What's new in **test-time scaling for large language models**?"

Get a concise, citation-backed summary within 30 minutes — enough to support a high-quality group meeting presentation.

### 6. Paper Review Preparation

Received a paper review invitation and need to understand the related work background:

> "Help me find key papers in **graph neural networks for drug discovery** — any breakthrough work recently?"

Quickly locate milestone work and latest advances in the field to support your review judgment.

### 7. Cross-Disciplinary Exploration

Looking for interdisciplinary opportunities between your field and others:

> "Survey the current state of **reinforcement learning in chip design (EDA)**."

Gap analysis automatically identifies mainstream directions and uncovered subtopics in this cross-disciplinary area.

### 8. Grant / Project Proposal

Need to argue the frontier significance and necessity of a research direction:

> "Survey research dynamics of **embodied AI in home service robots**, focusing on which technical bottlenecks remain unsolved."

The "negative trend analysis" and "future directions" sections of the report can be used directly in your proposal's significance and challenge statements.

---

## Deployment

This Skill supports dual-tool deployment for **Claude Code + Codex**. The Skill directory structure is fully compatible between both tools — one codebase, one entry point.

Claude Code and Codex load Skills from:

- **Global Skills**: `~/.claude/skills/` or `~/.codex/skills/` — available in any project
- **Project Skills**: `<project>/.claude/skills/` or `<project>/.codex/skills/` — available only within that project

### One-Click Deployment (Recommended)

Use `deploy.py` in the repository root for cross-platform one-click deployment:

```bash
# Global deployment (available in both tools)
python deploy.py --global

# Project-level only
python deploy.py --local

# Preview actions without executing
python deploy.py --dry-run --global

# Uninstall
python deploy.py --remove
```

Platform auto-adaptation: Linux/macOS uses symbolic links; Windows uses directory junctions (`mklink /J`).

Codex deployment first reads the `$CODEX_HOME` environment variable, falling back to `~/.codex/skills/` if not set.

### Manual Deployment

If you prefer to copy manually, copy the `academic-trend-analysis/` directory to the target locations:

```bash
# Global deployment
cp -r academic-trend-analysis ~/.claude/skills/
cp -r academic-trend-analysis ~/.codex/skills/

# Project-level deployment
mkdir -p .claude/skills .codex/skills
cp -r academic-trend-analysis .claude/skills/
cp -r academic-trend-analysis .codex/skills/

# Verify
ls ~/.claude/skills/academic-trend-analysis/SKILL.md
ls ~/.codex/skills/academic-trend-analysis/SKILL.md
```

> **Difference**: Global deployment is one-time and applies to all projects; project deployment only affects the current project. One-click deployment uses symbolic links / directory junctions, so source code changes take effect immediately without re-deployment.

---

## Usage

### Natural Language Trigger

No commands to memorize — just describe your need in everyday language:

```
Analyze the trend of X
Survey papers in the field of X
Research landscape of direction X
Help me search for papers on X and generate a survey
```

Trigger keywords include: 趋势, 前沿, 热点, 论文调研, 文献综述, research trend, academic survey, paper search, 领域分析, research landscape, literature review.

### Interaction Flow

The entire process consists of **5 human confirmation points + fully automatic stages**:

```
You: "Analyze the trend of hierarchical reinforcement learning"
     │
     ▼
┌─────────────────────────────────────┐
│ Stage 0: Environment Probe + Mode    │
│ Selection                           │
│ Agent detects BM25 / Milvus          │
│ availability                        │
│ ⛔ Presents 4-in-1 combo selection,  │
│   waits for confirmation             │
│   BM25/Milvus × Standard/Fast        │
└─────────────────┬───────────────────┘
                  ▼
           Choose Milvus?
┌─────────────────┬───────────────────┐
│ Yes             │ No                │
│ ⛔ Confirm       │                   │
│   embedding      │                   │
│   model & path   │                   │
└────────┬────────┘                   │
         ▼                            ▼
┌─────────────────────────────────────┐
│ Stage 1: Requirement Analysis        │
│ Standard → 5-layer Socratic dialogue │
│ Fast → 1-2 rounds of clarification  │
│ Agent web search → dialogue/Q&A     │
│ ⛔ Generates demand.json, waits      │
│   for "continue" confirmation       │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ Stage 2-8: Fully Automatic           │
│ Search → Store → Filter → Supplement │
│ → Grade → Prompt → Write → Save     │
│ Results shown after each step,       │
│ no waiting required                  │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ After report generation              │
│ ⛔ You can request revisions          │
│   (max 2 rounds)                    │
└─────────────────┬───────────────────┘
                  ▼
           Output: report.md
```

You can say "continue to the end" at any time to let the Agent run all remaining stages in one go.

---

## Technical Pipeline

8 automatically executed backend stages + optional revision loop:

| Stage | Action                                                                              | Output                      | Interaction                                                    |
| ----- | ----------------------------------------------------------------------------------- | --------------------------- | -------------------------------------------------------------- |
| 0     | Environment probe + mode selection                                                  | 4-in-1 combo selection      | ⛔ Retrieval mode (BM25/Milvus) + dialogue mode (Standard/Fast) |
| —     | Milvus path confirmation (Milvus only)                                              | Embedding model + data path | ⛔ Confirm env vars or ask user                                 |
| 1     | Requirement analysis (Standard: 5-layer dialogue / Fast: 1-2 rounds + gap analysis) | `demand.json`               | ⛔ Requirement confirmation                                     |
| 2     | Four-source paper search (arXiv / Semantic Scholar / OpenAlex / AlphaXiv)           | `paper_pre_list.json`       | Auto                                                           |
| 3     | Abstract storage (BM25 JSON or Milvus vector indexing)                              | `abstracts.json`            | Auto                                                           |
| 4     | Core paper filtering (BM25 relevance + title weighting)                             | `core_papers.json`          | Auto                                                           |
| 5     | Supplemental paper search (multi-keyword RRF fusion)                                | `supplement_papers.json`    | Auto                                                           |
| 5.5   | Paper quality grading (T1 top conference / T2 preprint / T3 pending verification)   | `quality_tiers.json`        | Auto                                                           |
| 6     | Build report prompt                                                                 | `report_prompt.md`          | Auto                                                           |
| 7     | Agent writes report following template                                              | `report_draft.md`           | Auto                                                           |
| 8     | Extract citations + re-map numbering + GB/T 7714 references                         | `report.md`                 | Auto                                                           |
| —     | Report revision (user-triggered, max 2 rounds)                                      | `report.md` (revised)       | ⛔ Collect feedback → re-run Stage 6-8                          |

All intermediate artifacts are saved under `data/YYYY-MM-DD-HH-MM-topic/` (e.g., `data/2026-06-04-12-00-hierarchical-reinforcement/`). Each run is automatically isolated for easy回溯 and comparison.

---

## Two Retrieval Modes + Two Dialogue Modes

### Retrieval Modes

| Mode               | Dependencies                         | Features                                               | Use Case                                                      |
| ------------------ | ------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------------- |
| **BM25** (default) | `requests`                           | Zero-config, millisecond-speed, keyword-based matching | Quick validation, first-time use, no GPU environment          |
| **Milvus**         | `pymilvus` + `sentence-transformers` | Semantic recall, BGE vector similarity                 | Pursuing highest retrieval quality, local vector DB available |

> BM25 retrieval on academic paper abstracts performs comparably to lightweight vector retrieval — recommended as the default. Switch to Milvus only when deep semantic recall is needed.

### Dialogue Modes

| Mode         | Interaction Depth                 | Features                                                                             | Use Case                                          |
| ------------ | --------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------- |
| **Standard** | 5-layer Socratic dialogue         | Scope → Dimensions → Evidence Standards → Bias Awareness → Contribution Articulation | Vague requirements, desire for deep clarification |
| **Fast**     | 1-2 rounds of quick clarification | Direct WebSearch + concise prompts                                                   | Already have a clear analysis target              |

> In Stage 0, the two modes combine into four options: `BM25+Standard`, `BM25+Fast`, `Milvus+Standard`, `Milvus+Fast`.

### Additional Milvus Configuration

When choosing Milvus mode, confirm the following:

1. **Embedding model path**: Reads environment variable `MILVUS_EMBEDDING_MODEL` first; if not set, the Agent asks you to provide it
2. **Database save path**: Reads environment variable `MILVUS_DATA_PATH` first; if not set, the Agent asks you to provide it

Both paths are written into `demand.json` and automatically read in subsequent stages — no need to specify them again.

Recommended model: [BAAI/bge-large-zh-v1.5](https://huggingface.co/BAAI/bge-large-zh-v1.5) (1024 dimensions).

> **Windows users**: If `python` or `pip` is not in your PATH, use `python -m pip install ...` or install within an Anaconda/Miniconda environment. This Skill was developed in a `conda activate agno` environment but does not强制 require conda.

---

## Project Structure

```
academic-trend-analysis/
├── SKILL.md                    # Skill definition and complete usage documentation
├── agents/                     # Agent instructions
│   ├── mode_selector.md        # Mode selector (Stage 0, 4-in-1 combo selection)
│   ├── demand_analyzer.md      # Demand analyzer (Stage 1, with 5-layer Socratic dialogue)
│   ├── paper_searcher.md       # Paper searcher (Stage 2)
│   ├── knowledge_manager.md    # Knowledge manager (Stage 3-5)
│   └── trend_reporter.md       # Trend reporter (Stage 6-8 + report revision)
├── lib/                        # Self-contained code library
│   ├── paper_search.py         # Multi-source search + deduplication + keyword expansion
│   ├── paper_retrieval.py      # BM25/Milvus retrieval + abstract storage
│   └── report_builder.py       # Prompt building + report saving
├── scripts/                    # Stage 0-8 executable scripts (auto-called by Agent)
├── references/                 # Process reference documents
├── templates/                  # Report generation templates
└── examples/                   # Complete execution examples
```

---

## Dependencies

Python 3.10+ environment. Dependencies are separated by mode — install only what you need:

### BM25 Mode (default, zero-config)

Only requires `requests`, uses keyword BM25 matching, suitable for most scenarios:

```bash
pip install -r academic-trend-analysis/requirements.txt
# Or install individually: pip install requests
```

### Milvus Vector Retrieval Mode (optional)

Requires additional vector retrieval dependencies, suitable for scenarios pursuing deep semantic recall:

```bash
pip install pymilvus sentence-transformers
```

**Embedding model path** and **database save path**:
When selecting Milvus mode, the Agent guides you to confirm in Stage 0:
- First reads environment variables `MILVUS_EMBEDDING_MODEL` / `MILVUS_DATA_PATH`
- If not set, the Agent interactively asks you to provide the paths
- After confirmation, paths are written to `demand.json` and automatically read in subsequent stages

You can also preset via environment variables:

```bash
# Linux / macOS
export MILVUS_EMBEDDING_MODEL=/path/to/bge-large-zh-v1.5
export MILVUS_DATA_PATH=./milvus_data

# Windows
set MILVUS_EMBEDDING_MODEL=C:\models\bge-large-zh-v1.5
set MILVUS_DATA_PATH=C:\milvus_data
```

Recommended model: [BAAI/bge-large-zh-v1.5](https://huggingface.co/BAAI/bge-large-zh-v1.5) (1024 dimensions)

---

## License

MIT
