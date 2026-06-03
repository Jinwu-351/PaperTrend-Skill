"""需求解析模块 — 将用户研究方向转化为结构化论文检索参数

功能:
- 关键词扩展（基于静态词库）
- 领域背景摘要（基于静态映射表）
- Tavily 网络搜索（可选，需用户提供 API key）
- 人在回路交互（可选，--interactive 标志）

三级能力:
    Level 1: Claude Code 路径（人在回路 + 网络搜索）— 由 Claude Code 预先构造 demand.json
    Level 2: Tavily 路径（用户提供 key）— 脚本内搜索 + 交互
    Level 3: Fallback（静态词库）— 与原行为一致
"""

import re
import json
import time
import sys
from pathlib import Path
from typing import List, Dict, Optional


# ════════════════════════════════════════════════════════════
# 静态词库（Fallback 路径，从 run_full.py 迁入）
# ════════════════════════════════════════════════════════════

_SEMANTIC_EXPANSIONS = {
    # 强化学习
    "reinforcement learning": ["deep reinforcement learning", "DRL", "policy gradient", "actor-critic", "Q-learning"],
    "rl": ["reinforcement learning", "deep reinforcement learning"],
    # 分层强化学习
    "hierarchical reinforcement learning": ["HRL", "options framework", "temporal abstraction", "skill discovery", "subgoal discovery", "option-critic"],
    "hrl": ["hierarchical reinforcement learning", "options framework", "temporal abstraction"],
    "options framework": ["option-critic", "temporal abstraction", "macro-actions"],
    "subgoal discovery": ["skill discovery", "hierarchical task decomposition", "goal space abstraction"],
    # Transformer / 大语言模型
    "transformer": ["attention mechanism", "self-attention", "large language model", "LLM", "pre-training"],
    "large language model": ["LLM", "language model", "pre-trained model", "foundation model", "GPT"],
    "llm": ["large language model", "language model", "foundation model"],
    # 计算机视觉
    "computer vision": ["image recognition", "object detection", "image classification", "CNN"],
    "image classification": ["convolutional neural network", "CNN", "resnet", "vision transformer"],
    # 自然语言处理
    "natural language processing": ["NLP", "text classification", "named entity recognition", "sentiment analysis"],
    "nlp": ["natural language processing", "text analysis", "language understanding"],
    # 图神经网络
    "graph neural network": ["GNN", "graph convolutional network", "GCN", "graph attention network", "GAT"],
    "gnn": ["graph neural network", "graph convolution", "message passing"],
    # 量子计算
    "quantum error correction": ["QEC", "stabilizer code", "fault tolerance", "syndrome measurement", "logical qubit"],
    "qec": ["quantum error correction", "stabilizer code", "fault tolerance"],
    "quantum computing": ["quantum algorithm", "quantum circuit", "qubit", "quantum supremacy"],
    # 联邦学习
    "federated learning": ["FL", "distributed learning", "privacy-preserving", "decentralized"],
    "fl": ["federated learning", "distributed machine learning"],
    # 对比学习
    "contrastive learning": ["self-supervised learning", "representation learning", "SimCLR", "MoCo"],
    "self-supervised learning": ["contrastive learning", "pretext task", "representation learning"],
    # 扩散模型
    "diffusion model": ["denoising diffusion", "DDPM", "score-based model", "generative model"],
    "diffusion models": ["denoising diffusion", "DDPM", "score-based model", "generative model"],
    # 多智能体
    "multi-agent": ["multi-agent system", "multi-agent reinforcement learning", "MARL", "cooperative learning"],
    "multi-agent reinforcement learning": ["MARL", "cooperative reinforcement learning", "competitive multi-agent"],
    "marl": ["multi-agent reinforcement learning", "cooperative learning"],
}

_SUMMARY_MAP = {
    "reinforcement learning": (
        "强化学习（RL）是机器学习的核心分支，通过与环境交互学习最优策略。"
        "深度强化学习（DRL）结合深度神经网络，在 Atari 游戏、Go、机器人控制等领域取得突破。"
        "近年趋势包括 offline RL、model-based RL、multi-agent RL、以及与大语言模型的结合。"
    ),
    "hierarchical reinforcement learning": (
        "分层强化学习（HRL）通过时间抽象和状态抽象将复杂任务分解为多层子任务，"
        "解决传统 RL 在长时域和稀疏奖励中的困难。核心方法包括 Options 框架、"
        "HIRO、HAC、Option-Critic 等。近年趋势涉及因果结构建模、LLM 辅助规划、"
        "以及在机器人、交通、金融等领域的广泛应用。"
    ),
    "large language model": (
        "大语言模型（LLM）基于 Transformer 架构，通过在大规模文本上预训练获得强大的语言理解和生成能力。"
        "从 GPT 系列到 LLaMA、Claude 等开源模型，LLM 在推理、代码生成、对话等任务中表现出色。"
        "当前趋势包括指令微调、RLHF、多模态融合、以及 Agent 化应用。"
    ),
    "transformer": (
        "Transformer 架构自 2017 年提出以来，已成为 NLP、CV、音频等领域的基础模型。"
        "核心机制包括 self-attention、multi-head attention 和 positional encoding。"
        "近年变体包括 Vision Transformer、Swin Transformer、以及高效 attention 机制。"
    ),
    "graph neural network": (
        "图神经网络（GNN）专门处理图结构数据，通过消息传递机制学习节点和图的表示。"
        "主要变体包括 GCN、GAT、GraphSAGE 等，广泛应用于推荐系统、药物发现、社交网络分析。"
    ),
    "contrastive learning": (
        "对比学习是自监督学习的核心方法，通过拉近正样本对、推开负样本对来学习表示。"
        "代表性方法包括 SimCLR、MoCo、BYOL 等，在视觉和 NLP 中均有广泛应用。"
    ),
    "diffusion model": (
        "扩散模型通过逐步去噪过程学习数据分布，在图像生成、音频合成等领域超越 GAN。"
        "代表性方法包括 DDPM、Stable Diffusion、DALL-E 等。"
    ),
    "federated learning": (
        "联邦学习允许多方在不共享原始数据的情况下协同训练模型，保护数据隐私。"
        "核心挑战包括通信效率、非 IID 数据、安全性和个性化。"
    ),
    "quantum error correction": (
        "量子纠错（QEC）是量子计算的核心挑战，通过编码和纠错机制保护量子信息免受噪声影响。"
        "主要方法包括稳定子码（stabilizer codes）、表面码（surface codes）、连续时间纠错等。"
    ),
}


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def expand_query_terms(query: str) -> list:
    """智能扩展搜索关键词（静态词库 fallback）

    规则:
    1. 原始查询
    2. 首字母缩写（2-5 个单词）
    3. 小写变体
    4. 语义扩展词（从词库匹配）

    返回去重后的前 5 个词。
    """
    terms = [query]
    words = query.split()

    # 首字母缩写
    if 2 <= len(words) <= 5:
        acronym = ''.join(w[0].upper() for w in words)
        terms.append(acronym)

    # 小写变体
    if query != query.lower():
        terms.append(query.lower())

    # 语义扩展
    query_lower = query.lower()
    for key, expansions in _SEMANTIC_EXPANSIONS.items():
        if key in query_lower or query_lower in key:
            terms.extend(expansions)
            break

    # 去重保序，限制 5 个
    seen = set()
    result = []
    for t in terms:
        t_lower = t.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            result.append(t)
            if len(result) >= 5:
                break
    return result


def generate_web_summary(query: str) -> str:
    """基于静态映射表生成领域背景摘要（fallback）"""
    query_lower = query.lower()
    for key, summary in _SUMMARY_MAP.items():
        if key in query_lower or query_lower in key:
            return summary

    return f"{query} 领域的研究趋势分析。"


# ════════════════════════════════════════════════════════════
# Tavily 网络搜索（可选路径）
# ════════════════════════════════════════════════════════════

def web_search_tavily(query: str, api_key: str, max_results: int = 10) -> list:
    """Tavily API 搜索，返回趋势摘要

    Args:
        query: 搜索关键词
        api_key: Tavily API key（用户提供）
        max_results: 最大结果数

    Returns:
        list of {title, content, url}
    """
    import requests

    url = "https://api.tavily.com/search"
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "query": f"{query} research trends latest advances",
        "api_key": api_key,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
    }

    for attempt in range(1, 4):
        try:
            resp = requests.post(url, json=data, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()

            results = []
            for item in result.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "url": item.get("url", ""),
                })

            # Tavily 返回的 answer 字段可直接作为领域摘要
            answer = result.get("answer", "")
            if answer:
                # 将 answer 插入第一条结果
                if results:
                    results[0]["answer"] = answer

            return results

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            if status in (429, 503) and attempt < 3:
                wait = min(2 ** attempt * 5, 60)
                print(f"  Tavily {status} 限流，等待 {wait}s")
                time.sleep(wait)
                continue
            print(f"  Tavily 搜索失败: {e}")
            return []

        except requests.exceptions.RequestException as e:
            print(f"  Tavily 搜索异常: {type(e).__name__}: {e}")
            return []

    return []


# ════════════════════════════════════════════════════════════
# 人在回路交互
# ════════════════════════════════════════════════════════════

def interactive_refine(query: str, web_results: Optional[list] = None) -> dict:
    """交互式澄清用户需求

    打印 2-3 个澄清问题，读取用户回答，返回扩展后的查询信息。

    Args:
        query: 用户原始查询
        web_results: Tavily 搜索结果（可选）

    Returns:
        dict with keys: refined_query, focus_areas, custom_terms, web_summary
    """
    print(f"\n--- 需求解析：人在回路 ---")
    print(f"研究方向: {query}")

    if web_results:
        print(f"网络搜索到 {len(web_results)} 条结果")
        # 展示搜索到的趋势信号
        for i, r in enumerate(web_results[:3], 1):
            title = r.get("title", "")[:80]
            print(f"  [{i}] {title}")
        # 如果有 answer 字段，提取为 web_summary
        answer = web_results[0].get("answer", "") if web_results else ""

    print()

    # 澄清问题模板
    questions = [
        ("您更关注理论方法还是实际应用？（理论 / 应用 / 两者都有）", "focus"),
        ("是否有特定的子方向或应用场景需要重点关注？（留空跳过）", "sub_topics"),
        ("时间范围是否需要调整？（留空默认近2年，格式如 2023-01-01）", "start_date"),
    ]

    answers = {}
    for q_text, q_key in questions:
        try:
            ans = input(f"  {q_text}\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            ans = ""
        if ans:
            answers[q_key] = ans

    # 构建返回
    result = {
        "refined_query": query,
        "focus_areas": answers.get("focus", ""),
        "custom_terms": [],
        "web_summary": answer if web_results and answer else "",
        "start_date_override": answers.get("start_date", ""),
    }

    # 如果用户提供了子方向，尝试解析为搜索词
    sub = answers.get("sub_topics", "")
    if sub:
        result["custom_terms"] = [t.strip() for t in re.split(r'[,、/]', sub) if t.strip()]

    print(f"--- 需求解析完成 ---\n")
    return result


# ════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════

def analyze_demand(
    query: str,
    mode: str = "bm25",
    tavily_key: Optional[str] = None,
    interactive: bool = False,
) -> dict:
    """需求解析主入口

    Args:
        query: 用户原始查询
        mode: 检索模式
        tavily_key: 用户提供的 Tavily API key（可选）
        interactive: 是否启用人在回路交互

    Returns:
        dict 兼容 demand.json 格式
    """
    from datetime import datetime

    now = datetime.now()
    two_years_ago = now.replace(year=now.year - 2)

    # Step 1: 网络搜索（如果有 Tavily key）
    web_results = None
    web_summary = ""
    if tavily_key:
        print("\n  正在通过 Tavily 搜索领域趋势...")
        web_results = web_search_tavily(query, tavily_key)
        if web_results:
            answer = web_results[0].get("answer", "")
            if answer:
                web_summary = answer
                print(f"  搜索完成: {len(web_results)} 条结果，已获取趋势摘要")

    # Step 2: 人在回路（如果启用）
    custom_terms = []
    start_date_override = ""
    if interactive:
        refined = interactive_refine(query, web_results)
        custom_terms = refined.get("custom_terms", [])
        if refined.get("web_summary") and not web_summary:
            web_summary = refined["web_summary"]
        start_date_override = refined.get("start_date_override", "")
        if refined.get("focus_areas"):
            custom_terms.append(refined["focus_areas"])

    # Step 3: 生成 query_terms
    base_terms = expand_query_terms(query)
    # 合并用户自定义词，去重保序，限 5 个
    if custom_terms:
        seen = set(t.lower() for t in base_terms)
        for t in custom_terms:
            if t.lower() not in seen and len(base_terms) < 5:
                seen.add(t.lower())
                base_terms.append(t)
            if len(base_terms) >= 5:
                break

    # Step 4: 生成 web_summary
    if not web_summary:
        web_summary = generate_web_summary(query)

    # Step 5: 构造 demand
    start_date = start_date_override if start_date_override else two_years_ago.strftime("%Y-%m-%d")

    demand = {
        "task": f"分析 {query} 的趋势",
        "query": query,
        "query_terms": base_terms[:5],
        "max_results": 25,
        "authors": None,
        "start_date": start_date,
        "end_date": now.strftime("%Y-%m-%d"),
        "categories": None,
        "sort_by": "relevance",
        "web_summary": web_summary,
        "retrieval_mode": mode,
    }

    return demand
