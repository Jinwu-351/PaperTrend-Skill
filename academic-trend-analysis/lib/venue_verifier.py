"""论文发表来源核实模块

核实策略：
1. 优先用 DOI 精确查询 Crossref（可靠）
2. 标题查询不可靠，留给 Agent 网络搜索复核

依赖：仅 requests（与 skill 其他模块一致）
"""

import requests
import time
from typing import Dict, List, Optional


class VenueVerifier:
    """论文来源核实器（API 部分）

    通过 Crossref DOI 查询核实论文的正式发表信息。
    """

    CROSSREF_API = "https://api.crossref.org/works"

    # 无效 venue 标记（这些值表示未核实或预印本）
    INVALID_VENUES = {"arxiv preprint", "arxiv", "来源待核实", "coRR", ""}

    def __init__(self, timeout: int = 15, mailto: str = None):
        """
        Args:
            timeout: HTTP 请求超时时间（秒）
            mailto: Crossref polite pool 邮箱（可选，提高速率）
        """
        self.timeout = timeout
        self.mailto = mailto

    def verify_by_doi(self, doi: str) -> Optional[Dict]:
        """通过 DOI 查询 Crossref

        Args:
            doi: DOI 字符串，格式 "10.xxxx/..."

        Returns:
            {"venue": str, "type": str, "source": "crossref_doi"} 或 None
        """
        if not doi or not doi.startswith("10."):
            return None

        url = f"{self.CROSSREF_API}/{doi}"
        params = {"mailto": self.mailto} if self.mailto else {}

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json().get("message", {})

            # 提取 venue（container-title 优先）
            container = data.get("container-title", [])
            venue = container[0] if container else ""

            # 提取 event 信息（会议）
            event = data.get("event", {})
            if not venue and event:
                venue = event.get("name", "")

            # 提取类型
            pub_type = data.get("type", "")

            if venue:
                return {
                    "venue": venue,
                    "type": pub_type,
                    "source": "crossref_doi"
                }
            return None

        except requests.exceptions.Timeout:
            print(f"  Crossref DOI 查询超时: {doi}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"  Crossref DOI 查询失败: {doi} - {e}")
            return None
        except Exception as e:
            print(f"  Crossref DOI 查询异常: {doi} - {e}")
            return None

    def verify_paper(self, paper: Dict) -> Dict:
        """核实单篇论文（仅 DOI 查询）

        Args:
            paper: 论文元数据字典

        Returns:
            更新后的论文元数据，可能包含：
            - venue: 更新后的来源信息
            - venue_verified_by: 核实来源 ("crossref_doi")
            - venue_updated: True（如果更新了 venue）
            - original_venue: 原始 venue（保存用于回溯）
            - needs_web_search: True（如果无法通过 API 核实）
        """
        # 如果已有有效 venue，跳过
        if self._has_valid_venue(paper):
            return paper

        # 保存原始 venue
        paper["original_venue"] = paper.get("venue", "")

        # 提取 DOI
        doi = self._extract_doi(paper)
        if doi:
            result = self.verify_by_doi(doi)
            if result:
                paper["venue"] = self._format_venue(result["venue"], result["type"])
                paper["venue_verified_by"] = result["source"]
                paper["venue_updated"] = True
                return paper

        # 无法通过 API 核实，标记为待网络搜索复核
        paper["needs_web_search"] = True
        return paper

    def verify_batch(self, papers: List[Dict], progress_callback=None) -> List[Dict]:
        """批量核实论文来源

        Args:
            papers: 论文列表
            progress_callback: 进度回调函数 (i, total, title, result)

        Returns:
            更新后的论文列表
        """
        results = []
        total = len(papers)

        for i, paper in enumerate(papers, 1):
            title = paper.get("title", "")[:50]
            result = self.verify_paper(paper)
            results.append(result)

            if progress_callback:
                progress_callback(i, total, title, result)

            # API 限流：每请求间隔 1 秒（Crossref polite pool 建议）
            if i < total:
                time.sleep(1)

        return results

    def _has_valid_venue(self, paper: Dict) -> bool:
        """检查是否已有有效的 venue（非预印本/待核实）"""
        venue = paper.get("venue", "")
        if not venue:
            return False
        return venue.lower().strip() not in self.INVALID_VENUES

    def _extract_doi(self, paper: Dict) -> Optional[str]:
        """从论文元数据中提取 DOI

        尝试顺序：
        1. entry_id 字段（以 "10." 开头）
        2. pdf_url 字段（包含 "doi.org/"）
        """
        # 从 entry_id 提取
        entry_id = paper.get("entry_id", "")
        if entry_id.startswith("10."):
            return entry_id

        # 从 pdf_url 提取
        pdf_url = paper.get("pdf_url", "")
        if "doi.org/" in pdf_url:
            return pdf_url.split("doi.org/")[-1]

        return None

    def _format_venue(self, venue: str, pub_type: str) -> str:
        """格式化 venue 名称

        Args:
            venue: 原始 venue 名称
            pub_type: 发表类型 (proceedings-article, journal-article 等)

        Returns:
            格式化后的 venue 字符串
        """
        if not venue:
            return "来源待核实"

        # 简化过长的会议名称（常见模式）
        simplifications = {
            "Digital Avionics Systems Conference": "DASC",
            "International Conference on": "IC",
            "IEEE/AIAA": "IEEE/AIAA",
        }

        result = venue
        for full, short in simplifications.items():
            if full in result and len(result) > 60:
                # 保留核心名称
                result = result.replace(full, short)
                break

        return result


def get_papers_needing_web_search(papers: List[Dict]) -> List[Dict]:
    """筛选需要网络搜索复核的论文

    Args:
        papers: 论文列表（已经过 API 核实）

    Returns:
        标记为 needs_web_search: true 的论文列表
    """
    return [p for p in papers if p.get("needs_web_search")]


def summarize_verification_results(papers: List[Dict]) -> Dict:
    """生成核实结果摘要

    Args:
        papers: 核实后的论文列表

    Returns:
        摘要字典 {total, verified_by_api, needs_web_search, already_valid}
    """
    total = len(papers)
    verified_by_api = sum(1 for p in papers if p.get("venue_verified_by") == "crossref_doi")
    needs_web_search = sum(1 for p in papers if p.get("needs_web_search"))
    already_valid = total - verified_by_api - needs_web_search

    return {
        "total": total,
        "verified_by_api": verified_by_api,
        "needs_web_search": needs_web_search,
        "already_valid": already_valid,
    }
