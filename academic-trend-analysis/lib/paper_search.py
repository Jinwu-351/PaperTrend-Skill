"""论文多源搜索 — 纯 Python，仅依赖 requests 和标准库

支持的来源:
- arXiv (通过 export.arxiv.org API, XML 解析)
- Semantic Scholar (https://api.semanticscholar.org)
- OpenAlex (https://api.openalex.org)
- AlphaXiv (https://api.alphaxiv.org + arxiv.org 元数据抓取)

统一论文元数据格式:
{
    "title": str,
    "file_name": str,
    "authors": List[str],
    "summary": str,
    "published": str,          # YYYY-MM-DD
    "pdf_url": str,
    "entry_id": str,           # 来源ID
    "source": str,             # arxiv|semantic_scholar|openalex|alpha_xiv
    "venue": str,
}
"""

import re
import json
import time
import random
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

# ─── 工具函数 ───

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str) -> str:
    name = _ILLEGAL_CHARS.sub('_', name).strip().rstrip('.')
    return name[:200] if len(name) > 200 else name


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


# ─── arXiv 搜索 (XML API) ───

class ArxivSearcher:
    """arXiv 论文搜索，通过 export.arxiv.org API"""

    API_URL = "http://export.arxiv.org/api/query"

    @classmethod
    def check_availability(cls) -> tuple:
        try:
            import requests
            resp = requests.get(
                cls.API_URL,
                params={"search_query": 'all:"test"', "max_results": "1"},
                timeout=10
            )
            return (resp.status_code == 200,
                    f"arXiv API {'可用' if resp.status_code == 200 else f'异常 ({resp.status_code})'}")
        except Exception as e:
            return False, f"arXiv API 不可用: {type(e).__name__}"

    def search(self, query: str, max_results: int = 25,
               categories: Optional[List[str]] = None,
               sort_by: str = "relevance") -> List[Dict]:
        import requests

        query_parts = [f'all:"{query}"']
        if categories:
            cat_q = " OR ".join(f"cat:{c}" for c in categories)
            query_parts.append(f"({cat_q})")
        final_query = " AND ".join(query_parts)

        sort_map = {
            "relevance": "relevance",
            "submitted": "submittedDate",
            "updated": "lastUpdatedDate",
        }
        sort_order = "descending"

        papers = []
        start = 0
        batch = min(max_results, 200)

        while len(papers) < max_results:
            params = {
                "search_query": final_query,
                "start": start,
                "max_results": batch,
                "sortBy": sort_map.get(sort_by, "relevance"),
                "sortOrder": sort_order,
            }
            resp = requests.get(self.API_URL, params=params, timeout=30)
            resp.raise_for_status()

            root = ET.fromstring(resp.content)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            entries = root.findall("atom:entry", ns)
            if not entries:
                break

            for entry in entries:
                if len(papers) >= max_results:
                    break

                title = entry.find("atom:title", ns).text.strip()
                title = re.sub(r'\s+', ' ', title)

                authors = []
                for a in entry.findall("atom:author", ns):
                    name = a.find("atom:name", ns)
                    if name is not None and name.text:
                        authors.append(name.text.strip())

                summary_el = entry.find("atom:summary", ns)
                summary = summary_el.text.strip() if summary_el is not None else ""
                summary = re.sub(r'\s+', ' ', summary)

                published = entry.find("atom:published", ns)
                pub_date = published.text[:10] if published is not None else ""

                entry_id = entry.find("atom:id", ns)
                entry_id_str = entry_id.text.strip() if entry_id is not None else ""
                arxiv_id = entry_id_str.split("/abs/")[-1] if "/abs/" in entry_id_str else entry_id_str

                pdf_url = ""
                for link in entry.findall("atom:link", ns):
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href", "")
                        break
                if not pdf_url:
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

                cats = [c.get("term", "") for c in entry.findall("atom:category", ns)]

                papers.append({
                    "title": title,
                    "file_name": sanitize_filename(title),
                    "authors": authors,
                    "summary": summary,
                    "published": pub_date,
                    "pdf_url": pdf_url,
                    "entry_id": f"arxiv:{arxiv_id}",
                    "categories": cats,
                    "source": "arxiv",
                    "venue": "arXiv preprint",
                })

            start += batch
            if len(entries) < batch:
                break
            time.sleep(3)  # arXiv 速率限制

        return papers


# ─── Semantic Scholar ───

class SemanticScholarSearcher:
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    FIELDS = "title,authors,abstract,publicationDate,externalIds,venue,url,tldr"

    @classmethod
    def check_availability(cls) -> tuple:
        try:
            import requests
            resp = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/ARXIV:2308.04079",
                timeout=10
            )
            return (resp.status_code == 200,
                    f"Semantic Scholar API {'可用' if resp.status_code == 200 else f'异常 ({resp.status_code})'}")
        except Exception as e:
            return False, f"Semantic Scholar API 不可用: {type(e).__name__}"

    def search(self, query: str, max_results: int = 25,
               year_range: Optional[tuple] = None) -> List[Dict]:
        import requests

        papers = []
        params = {"query": query, "fields": self.FIELDS, "limit": min(max_results, 100)}
        if year_range:
            params["year"] = f"{year_range[0]}-{year_range[1]}"

        for attempt in range(1, 4):
            try:
                time.sleep(3)
                resp = requests.get(self.BASE_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("data", []):
                    paper = self._convert(item)
                    if paper:
                        papers.append(paper)
                        if len(papers) >= max_results:
                            break
                break
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                if status in (429, 503) and attempt < 3:
                    wait = min(2 ** attempt * 5, 60)
                    wait = int(wait * (0.7 + random.random() * 0.3))
                    print(f"  Semantic Scholar {status} 限流，等待 {wait}s")
                    time.sleep(wait)
                    continue
                break
            except requests.exceptions.RequestException:
                break

        return papers

    def _convert(self, item: Dict) -> Optional[Dict]:
        title = item.get("title")
        if not title:
            return None
        authors_data = item.get("authors", []) or []
        authors = [a.get("name", "") for a in authors_data if a.get("name")]
        external_ids = item.get("externalIds", {}) or {}
        entry_id = external_ids.get("ArXiv") or external_ids.get("DOI") or ""
        pub_date = item.get("publicationDate", "") or "unknown"
        venue = item.get("venue", "") or ""
        if not venue and "arxiv" in (item.get("url", "") or ""):
            venue = "arXiv preprint"
        summary = item.get("abstract", "") or ""
        if not summary:
            tldr = item.get("tldr")
            if tldr and isinstance(tldr, dict):
                summary = tldr.get("text", "")
        pdf_url = ""
        if external_ids.get("ArXiv"):
            pdf_url = f"https://arxiv.org/pdf/{external_ids['ArXiv']}"
        elif external_ids.get("DOI"):
            pdf_url = f"https://doi.org/{external_ids['DOI']}"
        return {
            "title": title,
            "file_name": sanitize_filename(title),
            "authors": authors,
            "summary": summary,
            "published": pub_date,
            "pdf_url": pdf_url,
            "entry_id": entry_id,
            "categories": [],
            "source": "semantic_scholar",
            "venue": venue,
        }


# ─── AlphaXiv ───

class AlphaXivSearcher:
    SEARCH_URL = "https://api.alphaxiv.org/search/v2/paper/fast"
    ARXIV_ABS_URL = "https://arxiv.org/abs/{paper_id}"

    @classmethod
    def check_availability(cls) -> tuple:
        try:
            import requests
            resp = requests.get(cls.SEARCH_URL, params={"q": "test", "includePrivate": "false"}, timeout=10)
            return (resp.status_code == 200,
                    f"AlphaXiv API {'可用' if resp.status_code == 200 else f'异常 ({resp.status_code})'}")
        except Exception as e:
            return False, f"AlphaXiv API 不可用: {type(e).__name__}"

    def search(self, query: str, max_results: int = 25,
               year_range: Optional[tuple] = None) -> List[Dict]:
        import requests

        papers = []
        search_results = []
        for attempt in range(1, 4):
            try:
                time.sleep(1)
                resp = requests.get(self.SEARCH_URL, params={"q": query, "includePrivate": "false"}, timeout=20)
                resp.raise_for_status()
                search_results = resp.json()
                break
            except (requests.exceptions.HTTPError, requests.exceptions.RequestException):
                if attempt >= 3:
                    return papers
                time.sleep(2 * attempt)

        for item in search_results[:max_results]:
            paper_id = item.get("paperId", "")
            if not paper_id:
                continue
            if year_range:
                pub_year = self._extract_year(paper_id)
                if pub_year and (pub_year < year_range[0] or pub_year > year_range[1]):
                    continue
            paper = self._fetch_metadata(paper_id)
            if paper:
                papers.append(paper)
                if len(papers) >= max_results:
                    break
            time.sleep(0.5)

        return papers

    def _extract_year(self, paper_id: str) -> Optional[int]:
        m = re.match(r'(\d{2})\d{2}\.', paper_id)
        return (2000 + int(m.group(1))) if m else None

    def _fetch_metadata(self, paper_id: str) -> Optional[Dict]:
        import requests
        url = self.ARXIV_ABS_URL.format(paper_id=paper_id)
        try:
            resp = requests.get(url, headers={"User-Agent": "AutoPaperSearcher/1.0"}, timeout=15)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._parse_html(resp.text, paper_id)
        except Exception:
            return None

    def _parse_html(self, html: str, paper_id: str) -> Optional[Dict]:
        title_m = re.search(r'<title>(?:\[\d+\.\d+\]\s*)?(.*?)</title>', html)
        title = title_m.group(1).strip() if title_m else ""
        if not title:
            return None
        authors = re.findall(r'citation_author" content="(.*?)"', html)
        abs_m = re.search(r'citation_abstract" content="(.*?)"', html, re.DOTALL)
        abstract = re.sub(r'\s+', ' ', abs_m.group(1).strip()) if abs_m else ""
        date_m = re.search(r'citation_online_date" content="(.*?)"', html)
        pub_date = date_m.group(1) if date_m else "unknown"
        pdf_m = re.search(r'citation_pdf_url" content="(.*?)"', html)
        pdf_url = pdf_m.group(1) if pdf_m else f"https://arxiv.org/pdf/{paper_id}.pdf"
        return {
            "title": title,
            "file_name": sanitize_filename(title),
            "authors": authors,
            "summary": abstract,
            "published": pub_date,
            "pdf_url": pdf_url,
            "entry_id": f"arxiv:{paper_id}",
            "categories": [],
            "source": "alpha_xiv",
            "venue": "arXiv preprint",
        }


# ─── OpenAlex ───

class OpenAlexSearcher:
    BASE_URL = "https://api.openalex.org/works"

    @classmethod
    def check_availability(cls) -> tuple:
        try:
            import requests
            resp = requests.get(cls.BASE_URL, params={"filter": "title.search:test", "per_page": "1"}, timeout=10)
            return (resp.status_code == 200,
                    f"OpenAlex API {'可用' if resp.status_code == 200 else f'异常 ({resp.status_code})'}")
        except Exception as e:
            return False, f"OpenAlex API 不可用: {type(e).__name__}"

    def search(self, query: str, max_results: int = 25,
               year_range: Optional[tuple] = None) -> List[Dict]:
        import requests

        papers = []
        params = {
            "filter": f"title.search:{query}",
            "per_page": min(max_results, 200),
            "select": "title,abstract_inverted_index,authorships,publication_date,primary_location,doi,ids,publication_year",
        }
        for attempt in range(1, 4):
            try:
                resp = requests.get(self.BASE_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("results", []):
                    pub_year = item.get("publication_year")
                    if year_range and pub_year:
                        if pub_year < year_range[0] or pub_year > year_range[1]:
                            continue
                    paper = self._convert(item)
                    if paper:
                        papers.append(paper)
                        if len(papers) >= max_results:
                            break
                break
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                if status in (429, 503) and attempt < 3:
                    wait = min(2 ** attempt * 5, 60)
                    print(f"  OpenAlex {status} 限流，等待 {wait}s")
                    time.sleep(wait)
                    continue
                break
            except requests.exceptions.RequestException:
                break

        return papers

    def _convert(self, item: Dict) -> Optional[Dict]:
        title = item.get("title")
        if not title:
            return None
        authors = []
        for a in item.get("authorships", []) or []:
            author = a.get("author", {}) or {}
            name = author.get("display_name", "")
            if name:
                authors.append(name)
        entry_id = item.get("doi", "") or item.get("ids", {}).get("openalex", "") or ""
        pub_date = item.get("publication_date", "") or ""
        if not pub_date:
            pub_year = item.get("publication_year")
            pub_date = f"{pub_year}-01-01" if pub_year else "unknown"
        primary = item.get("primary_location", {}) or {}
        source = primary.get("source", {}) or {}
        venue = source.get("display_name", "") or ""
        abstract = self._reconstruct_abstract(item.get("abstract_inverted_index"))
        pdf_url = primary.get("pdf_url", "") or ""
        return {
            "title": title,
            "file_name": sanitize_filename(title),
            "authors": authors,
            "summary": abstract,
            "published": pub_date,
            "pdf_url": pdf_url,
            "entry_id": entry_id,
            "categories": [],
            "source": "openalex",
            "venue": venue,
        }

    def _reconstruct_abstract(self, inv: Optional[Dict]) -> str:
        if not inv:
            return ""
        words = []
        for word, positions in inv.items():
            for pos in positions:
                words.append((pos, word))
        words.sort()
        return " ".join(w for _, w in words)


# ─── 关键词扩展 ───

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
    # 3D 视觉 / 图形学
    "gaussian splatting": ["3DGS", "novel view synthesis", "3D scene representation", "differentiable rendering", "point-based rendering"],
    "3d gaussian splatting": ["3DGS", "novel view synthesis", "3D scene representation", "differentiable rendering", "real-time rendering"],
    "3dgs": ["3D Gaussian Splatting", "gaussian splatting", "novel view synthesis", "3D scene representation"],
    "neural radiance field": ["NeRF", "novel view synthesis", "implicit neural representation", "volume rendering", "ray marching"],
    "nerf": ["Neural Radiance Fields", "novel view synthesis", "implicit neural representation", "volume rendering"],
    "novel view synthesis": ["view synthesis", "light field rendering", "neural rendering", "3D reconstruction"],
    "3d reconstruction": ["structure from motion", "multi-view stereo", "MVS", "depth estimation", "point cloud"],
    "differentiable rendering": ["neural rendering", "inverse rendering", "differentiable rasterization", "volume rendering"],
    # SLAM / 视觉定位
    "visual slam": ["simultaneous localization and mapping", "visual odometry", "loop closure", "pose estimation"],
    "slam": ["simultaneous localization and mapping", "visual odometry", "pose estimation", "loop closure"],
}


def expand_query_terms(query: str) -> list:
    """智能扩展搜索关键词

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
            break  # 只匹配第一个命中，避免过度扩展

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


_SEMANTIC_SUMMARIES = {
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
    # 3D 视觉 / 图形学
    "gaussian splatting": (
        "3D Gaussian Splatting（3DGS）是 2023 年 SIGGRAPH 提出的革命性 3D 场景表示方法，"
        "使用可微各向异性 3D 高斯基元实现实时高保真新视角合成，渲染速度比 NeRF 快 2-3 个数量级。"
        "核心优势包括显式表示、快速训练（分钟级）、实时渲染（≥30 FPS）。"
        "研究方向涵盖压缩存储、动态 4D 场景、SLAM 集成、自动驾驶、Avatar 生成等。"
    ),
    "3d gaussian splatting": (
        "3D Gaussian Splatting（3DGS）是 2023 年 SIGGRAPH 提出的革命性 3D 场景表示方法，"
        "使用可微各向异性 3D 高斯基元实现实时高保真新视角合成，渲染速度比 NeRF 快 2-3 个数量级。"
        "核心优势包括显式表示、快速训练（分钟级）、实时渲染（≥30 FPS）。"
        "研究方向涵盖压缩存储、动态 4D 场景、SLAM 集成、自动驾驶、Avatar 生成等。"
    ),
    "3dgs": (
        "3DGS（3D Gaussian Splatting）使用各向异性 3D 高斯基元进行显式场景表示和新视角合成，"
        "自 2023 年提出以来迅速成为 3D 视觉主流方法。研究热点包括 4D 动态场景、压缩优化、SLAM 集成等。"
    ),
    "neural radiance field": (
        "神经辐射场（NeRF）通过多层感知机隐式表示 3D 场景的密度和颜色，实现高质量新视角合成。"
        "自 2020 年提出后迅速发展出多种变体：Instant-NGP 加速训练、Mip-NeRF 处理多尺度、"
        "NeRF-W 处理野外照片等。当前 3DGS 方法在速度上超越了 NeRF，但 NeRF 的隐式表示仍在某些场景有优势。"
    ),
    "nerf": (
        "NeRF（Neural Radiance Fields）通过隐式 MLP 表示 3D 场景，结合体积渲染实现新视角合成。"
        "主要变体包括 Instant-NGP（哈希编码加速）、Mip-NeRF（抗锯齿）、NeRF-W（野外场景）等。"
        "当前趋势是与 3DGS 方法融合，取长补短。"
    ),
    "novel view synthesis": (
        "新视角合成（NVS）是计算机视觉和图形学的核心任务，从有限视角图像生成未见过视角的照片级真实感图像。"
        "主流方法包括基于光场的传统方法、NeRF 隐式表示、以及 3DGS 显式高斯表示。"
        "挑战包括稀疏视角重建、动态场景处理、大场景可扩展性。"
    ),
    "differentiable rendering": (
        "可微渲染是通过可微分方式将 3D 场景表示映射为 2D 图像的渲染管线，支持基于梯度的 3D 逆向优化。"
        "包括可微光线追踪、可微光栅化、体积渲染等方法。3DGS 是可微光栅化的最新成功应用。"
    ),
}


def generate_web_summary(query: str) -> str:
    """基于 query 生成领域背景摘要"""
    query_lower = query.lower()
    for key, summary in _SEMANTIC_SUMMARIES.items():
        if key in query_lower or query_lower in key:
            return summary
    return f"{query} 领域的研究趋势分析。"


# ─── 多源搜索编排 ───

def search_all_sources(query: str, max_results: int = 25,
                       categories: Optional[List[str]] = None,
                       year_range: Optional[tuple] = None,
                       sort_by: str = "relevance") -> tuple:
    """多源搜索论文

    Args:
        query: 搜索关键词
        max_results: 每源最大结果数
        categories: arXiv 类别列表
        year_range: (start_year, end_year)
        sort_by: relevance|submitted|updated

    Returns:
        (papers, report) — 论文列表和统计报告
    """
    all_papers = []
    sources_count = {}
    errors = {}

    # 1. arXiv
    try:
        arxiv = ArxivSearcher()
        papers = arxiv.search(query, max_results, categories, sort_by)
        all_papers.extend(papers)
        sources_count["arxiv"] = len(papers)
    except Exception as e:
        errors["arxiv"] = str(e)
        sources_count["arxiv"] = 0

    # 2. Semantic Scholar
    try:
        ss = SemanticScholarSearcher()
        papers = ss.search(query, max_results, year_range)
        all_papers.extend(papers)
        sources_count["semantic_scholar"] = len(papers)
    except Exception as e:
        errors["semantic_scholar"] = str(e)
        sources_count["semantic_scholar"] = 0

    # 3. AlphaXiv
    try:
        ax = AlphaXivSearcher()
        papers = ax.search(query, max_results, year_range)
        all_papers.extend(papers)
        sources_count["alpha_xiv"] = len(papers)
    except Exception as e:
        errors["alpha_xiv"] = str(e)
        sources_count["alpha_xiv"] = 0

    # 4. OpenAlex
    try:
        oa = OpenAlexSearcher()
        papers = oa.search(query, max_results, year_range)
        all_papers.extend(papers)
        sources_count["openalex"] = len(papers)
    except Exception as e:
        errors["openalex"] = str(e)
        sources_count["openalex"] = 0

    report = f"多源搜索: {' | '.join(f'{k}: {v}篇' for k, v in sources_count.items())}，合并后总计 {len(all_papers)} 篇"
    if errors:
        report += f"；异常: {' | '.join(f'{k}={v}' for k, v in errors.items())}"

    return all_papers, report


def search_multi(queries: List[str], max_results: int = 25,
                 categories: Optional[List[str]] = None,
                 year_range: Optional[tuple] = None) -> tuple:
    """多关键词搜索，合并后执行跨来源去重

    Returns:
        (all_papers, deduped_papers, reports) — 所有论文、去重后论文、各阶段报告
    """
    all_papers = []
    reports = []

    for i, query in enumerate(queries, 1):
        print(f"\n=== [{i}/{len(queries)}] 搜索: {query} ===")
        papers, report = search_all_sources(
            query, max_results, categories, year_range
        )
        reports.append(f"[{i}] {query} → {report}")
        all_papers.extend(papers)

    # 跨来源去重
    deduped = _deduplicate(all_papers)
    removed = len(all_papers) - len(deduped)
    reports.append(f"跨来源去重: {len(all_papers)} → {len(deduped)} (去除 {removed} 篇重复)")

    return all_papers, deduped, reports


def deduplicate(papers: List[Dict]) -> List[Dict]:
    """标题归一化去重，保留信息更完整的版本"""
    return _deduplicate(papers)


def _deduplicate(papers: List[Dict]) -> List[Dict]:
    deduped = {}
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        nt = normalize_title(paper.get("title", ""))
        if not nt:
            continue
        if nt not in deduped:
            deduped[nt] = paper
        else:
            existing = deduped[nt]
            if bool(paper.get("venue")) and not bool(existing.get("venue")):
                deduped[nt] = paper
            elif len(paper.get("authors", [])) > len(existing.get("authors", [])):
                deduped[nt] = paper
    return list(deduped.values())


# ─── 文件存储 ───

def save_papers(data_dir: Path, papers: List[Dict], filename: str = "paper_pre_list.json"):
    path = data_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(papers, f, indent=4, ensure_ascii=False)


def load_papers(data_dir: Path, filename: str = "paper_pre_list.json") -> List[Dict]:
    path = data_dir / filename
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
