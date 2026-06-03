#!/usr/bin/env python3
"""Stage 5.5: 文献质量分级

在 Stage 5（补充论文检索）之后、Stage 6（构建 Prompt）之前执行，
对全体论文（核心 + 补充）进行 T1/T2/T3 三级质量标注。
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 将 scripts 目录加入路径以加载 _guard
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
from _guard import check_user_confirmed


# ============ 已知会议/期刊分级表 ============

# T1: 经同行评议的知名会议/期刊
T1_VENUES = [
    # 机器人
    "IEEE Transactions on Robotics", "IEEE Robotics and Automation Letters",
    "International Journal of Robotics Research", "Journal of Field Robotics",
    "IEEE International Conference on Robotics and Automation", "ICRA",
    "IEEE/RSJ International Conference on Intelligent Robots and Systems", "IROS",
    "Robotics: Science and Systems", "RSS",
    "Conference on Robot Learning", "CoRL",
    "International Conference on Soft Robotics", "RoboSoft",
    "IEEE Robotics and Automation Magazine",
    "Frontiers in Robotics and AI",
    "Science Robotics",
    # 计算机视觉 / AI
    "IEEE Conference on Computer Vision and Pattern Recognition", "CVPR",
    "International Conference on Computer Vision", "ICCV",
    "European Conference on Computer Vision", "ECCV",
    "Neural Information Processing Systems", "NeurIPS", "NIPS",
    "International Conference on Machine Learning", "ICML",
    "International Conference on Learning Representations", "ICLR",
    "AAAI Conference on Artificial Intelligence", "AAAI",
    "International Joint Conference on Artificial Intelligence", "IJCAI",
    "Conference on Empirical Methods in Natural Language Processing", "EMNLP",
    "Annual Meeting of the Association for Computational Linguistics", "ACL",
    "North American Chapter of the Association for Computational Linguistics", "NAACL",
    "IEEE Transactions on Pattern Analysis and Machine Intelligence", "TPAMI",
    "International Journal of Computer Vision", "IJCV",
    "Journal of Machine Learning Research", "JMLR",
    # 传感器 / 控制 / 机电
    "IEEE Sensors Journal", "IEEE Transactions on Instrumentation and Measurement",
    "IEEE Transactions on Industrial Electronics",
    "IEEE Transactions on Automation Science and Engineering",
    "IEEE Transactions on Control Systems Technology",
    "IEEE/ASME Transactions on Mechatronics",
    "Sensors and Actuators",
    "Actuators",
    "Measurement Science and Technology",
    # 航天 / 工程
    "Journal of Guidance, Control, and Dynamics",
    "Acta Astronautica", "Advances in Space Research",
    "IEEE Aerospace Conference",
    "AIAA", "AIAA Journal",
    # 医学机器人
    "IEEE Transactions on Biomedical Engineering",
    "International Journal of Computer Assisted Radiology and Surgery",
    "IEEE Transactions on Medical Imaging",
    "Medical Image Analysis",
    # 交叉学科
    "Nature", "Science", "Nature Machine Intelligence",
    "Proceedings of the National Academy of Sciences", "PNAS",
    "Scientific Reports",
    "Bioinspiration & Biomimetics",
    "CIRP Annals",
    "Engineering Research Express",
    # 其他已知会议
    "International Conference on Space Robotics", "iSpaRo",
    "Offshore Technology Conference",
    "Digital Discovery",
    "Applied Sciences",
    "Transactions on GIS",
    "Italian National Conference on Sensors",
    "International Conference on Networking and Communications", "ICNWC",
]

# T2: 已知预印本平台
T2_SOURCES = [
    "arxiv.org", "arXiv", "arxiv",
    "biorxiv.org", "bioRxiv", "biorxiv",
    "Preprints.org",
    "Research Square",
    "TechRxiv",
    "SSRN",
    "ChemRxiv",
    "medRxiv",
]

# T3: 需进一步验证的来源
T3_INDICATORS = [
    "semantic_scholar", "openalex",
    "unknown", "unkn",
]


def classify_tier(paper: Dict) -> Tuple[str, str, str]:
    """对单篇论文进行质量分级

    Returns:
        (tier, reason, detail)
    """
    venue = (paper.get("venue") or "").strip()
    source = (paper.get("source") or "").strip()
    title = (paper.get("title") or "").strip()
    entry_id = (paper.get("entry_id") or "").strip()
    published = (paper.get("published") or "").strip()

    combined_info = f"{venue} {source} {entry_id} {title}"

    # Rule 1: 匹配 T1 已知会议/期刊
    for t1_name in T1_VENUES:
        # Case-insensitive substring match
        if t1_name.lower() in combined_info.lower():
            # 进一步区分: 会议论文集 vs. 期刊
            is_journal = any(kw in t1_name for kw in ["Transactions", "Journal", "Letters",
                                                        "Magazine", "Review", "CIRP",
                                                        "Actuators", "Engineering",
                                                        "Bioinspiration", "Sensors",
                                                        "Measurement"])
            venue_type = "期刊" if is_journal else "会议"
            return ("T1", f"经同行评议 ({venue_type}): {t1_name}", venue_type)

    # Rule 2: 匹配预印本平台
    for t2_src in T2_SOURCES:
        if t2_src.lower() in combined_info.lower():
            return ("T2", f"预印本 (未同行评议): {t2_src}", "预印本")

    # Rule 3: 匹配待核实来源
    for t3_ind in T3_INDICATORS:
        if t3_ind in combined_info.lower():
            return ("T3", f"来源待核实: {t3_ind}，需查DOI/会议/期刊", "待核实")

    # Rule 4: 发布年份推断 — 2026年论文大概率是预印本
    if published and len(published) >= 4:
        year = published[:4]
        if year == "2026":
            return ("T2", "推断为预印本 (2026年发表，多数尚未经同行评议)", "预印本")

    # Default: T3 未分类
    return ("T3", "无法自动分类，建议手动核验", "未分类")


def run_quality_tier(data_dir: Path) -> Dict:
    """执行文献质量分级

    Args:
        data_dir: session 数据目录

    Returns:
        分级结果字典
    """
    core_path = data_dir / "core_papers.json"
    supp_path = data_dir / "supplement_papers.json"

    core_papers = []
    supplement_papers = []

    if core_path.exists():
        with open(core_path) as f:
            core_papers = json.load(f)

    if supp_path.exists():
        with open(supp_path) as f:
            supplement_papers = json.load(f)

    all_papers = core_papers + supplement_papers

    # 分级
    results = {"T1": [], "T2": [], "T3": []}
    for paper in all_papers:
        tier, reason, detail = classify_tier(paper)
        paper["quality_tier"] = tier
        paper["quality_reason"] = reason
        paper["quality_detail"] = detail
        results[tier].append({
            "title": paper.get("title", "Unknown"),
            "venue": paper.get("venue", ""),
            "source": paper.get("source", ""),
            "published": paper.get("published", ""),
            "reason": reason,
        })

    # 统计
    total = len(all_papers)
    summary = {
        "total": total,
        "T1_count": len(results["T1"]),
        "T1_pct": round(len(results["T1"]) / total * 100, 1) if total else 0,
        "T2_count": len(results["T2"]),
        "T2_pct": round(len(results["T2"]) / total * 100, 1) if total else 0,
        "T3_count": len(results["T3"]),
        "T3_pct": round(len(results["T3"]) / total * 100, 1) if total else 0,
        "T1_list": results["T1"],
        "T2_list": results["T2"],
        "T3_list": results["T3"],
    }

    # 保存分级结果
    output_path = data_dir / "quality_tiers.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 更新 core/supplement 文件（附加 tier 信息）
    if core_papers:
        with open(core_path, 'w', encoding='utf-8') as f:
            json.dump(core_papers, f, indent=2, ensure_ascii=False)
    if supplement_papers:
        with open(supp_path, 'w', encoding='utf-8') as f:
            json.dump(supplement_papers, f, indent=2, ensure_ascii=False)

    # 打印人类可读报告
    _print_report(summary, output_path)

    return summary


def _print_report(summary: Dict, output_path: Path):
    """打印终端报告"""
    print(f"Stage 5.5: 文献质量分级")
    print(f"  论文总数: {summary['total']}")
    print(f"  T1 (同行评议): {summary['T1_count']} 篇 ({summary['T1_pct']}%)")
    for p in summary["T1_list"]:
        print(f"    ✓ {p['title'][:100]}")
        print(f"      {p['reason']}")
    print(f"  T2 (预印本):    {summary['T2_count']} 篇 ({summary['T2_pct']}%)")
    if summary["T2_list"]:
        print(f"    (代表性: {summary['T2_list'][0]['title'][:80]})")
    print(f"  T3 (待核实):    {summary['T3_count']} 篇 ({summary['T3_pct']}%)")
    if summary["T3_list"]:
        print(f"    (代表性: {summary['T3_list'][0]['title'][:80]})")

    # 风险提示
    t2t3_pct = summary["T2_pct"] + summary["T3_pct"]
    if t2t3_pct > 60:
        print(f"\n  ⚠️  风险提示: {t2t3_pct}% 论文来自预印本或未核实来源，趋势结论需谨慎引用。")
    elif t2t3_pct > 30:
        print(f"\n  ⚡ 注意: {t2t3_pct}% 论文来自预印本或未核实来源，建议在报告中声明。")
    else:
        print(f"\n  ✅ 文献质量良好，{summary['T1_pct']}% 经同行评议。")

    print(f"\nStage 5.5 完成: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python stage5_5_quality_tier.py <data_dir>")
        sys.exit(1)

    data_dir = Path(sys.argv[1])
    if not data_dir.exists():
        print(f"错误: 目录不存在 {data_dir}")
        sys.exit(1)

    # 🛑 守卫检查：确认 Stage 1 已被用户确认
    check_user_confirmed(data_dir)

    run_quality_tier(data_dir)


if __name__ == "__main__":
    main()
