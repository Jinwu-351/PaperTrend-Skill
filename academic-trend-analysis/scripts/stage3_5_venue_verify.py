#!/usr/bin/env python3
"""Stage 3.5: 论文来源核实（API 部分）

用法:
    python stage3_5_venue_verify.py <data_dir> [--mailto email@example.com]

说明:
    - 从 abstracts.json 读取论文
    - 通过 Crossref DOI 查询核实正式发表信息
    - 更新 abstracts.json 中的 venue 字段
    - 标记需要网络搜索复核的论文（needs_web_search: true）
    - 输出核实报告 venue_verification_report.json
    - 输出待网络搜索列表 papers_needing_web_search.json

依赖: requests, 标准库
"""

import sys
import json
from pathlib import Path

# 将 lib 和 scripts 目录加入路径
script_dir = Path(__file__).resolve().parent
lib_dir = script_dir.parent / "lib"
sys.path.insert(0, str(lib_dir))
sys.path.insert(0, str(script_dir))

from venue_verifier import VenueVerifier, get_papers_needing_web_search, summarize_verification_results
from _guard import check_user_confirmed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    data_dir = Path(sys.argv[1])

    # 解析可选参数
    mailto = None
    if "--mailto" in sys.argv:
        idx = sys.argv.index("--mailto")
        if idx + 1 < len(sys.argv):
            mailto = sys.argv[idx + 1]

    # 🛑 守卫检查：确认 Stage 1 已被用户确认
    check_user_confirmed(data_dir)

    # 读取论文
    abstracts_path = data_dir / "abstracts.json"
    if not abstracts_path.exists():
        print(f"错误: 未找到 {abstracts_path}，请先运行 Stage 3")
        sys.exit(1)

    with open(abstracts_path, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    if not papers:
        print("错误: abstracts.json 为空")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Stage 3.5: 论文来源核实（API 部分）")
    print(f"{'='*60}")
    print(f"  待核实论文: {len(papers)} 篇")
    if mailto:
        print(f"  Crossref polite pool: {mailto}")

    # 执行核实
    verifier = VenueVerifier(mailto=mailto)

    verified_count = 0
    needs_search_count = 0
    already_valid_count = 0

    def progress_callback(i, total, paper_title, result):
        nonlocal verified_count, needs_search_count, already_valid_count
        if result.get("venue_updated"):
            verified_count += 1
            venue_display = result.get('venue', '')[:40]
            print(f"  [{i}/{total}] ✅ {paper_title}... → {venue_display}")
        elif result.get("needs_web_search"):
            needs_search_count += 1
            print(f"  [{i}/{total}] ⏳ {paper_title}... → 待网络搜索复核")
        else:
            already_valid_count += 1
            venue_display = result.get('venue', '')[:30]
            print(f"  [{i}/{total}] — {paper_title}... → 已有 venue ({venue_display})")

    print()
    verified_papers = verifier.verify_batch(papers, progress_callback=progress_callback)

    # 保存更新后的论文
    with open(abstracts_path, 'w', encoding='utf-8') as f:
        json.dump(verified_papers, f, indent=4, ensure_ascii=False)

    # 获取需要网络搜索的论文
    needs_search = get_papers_needing_web_search(verified_papers)

    # 保存待复核列表（供 Agent WebSearch 使用）
    needs_search_path = data_dir / "papers_needing_web_search.json"
    needs_search_data = [{
        "index": i,  # 在 abstracts.json 中的索引（从1开始）
        "title": p.get("title", ""),
        "authors": p.get("authors", [])[:3],  # 仅保留前3位作者
        "year": p.get("published", "")[:4],
        "entry_id": p.get("entry_id", ""),
        "source": p.get("source", ""),
    } for i, p in enumerate(needs_search, 1)]

    with open(needs_search_path, 'w', encoding='utf-8') as f:
        json.dump(needs_search_data, f, indent=4, ensure_ascii=False)

    # 生成核实报告
    report = summarize_verification_results(verified_papers)
    report["mailto"] = mailto
    report["needs_search_details"] = needs_search_data

    report_path = data_dir / "venue_verification_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    # 输出统计
    print(f"\n{'─'*60}")
    print(f"Stage 3.5 完成:")
    print(f"  ✅ API 核实成功: {verified_count} 篇")
    print(f"  ⏳ 待网络搜索:  {needs_search_count} 篇")
    print(f"  —  已有有效 venue: {already_valid_count} 篇")
    print(f"{'─'*60}")

    if needs_search_count > 0:
        print(f"\n下一步: Agent 读取 {needs_search_path} 并执行网络搜索复核")
    else:
        print(f"\n所有论文已通过 API 核实，无需网络搜索复核")

    print(f"\n输出文件:")
    print(f"  - {abstracts_path}")
    print(f"  - {report_path}")
    if needs_search_count > 0:
        print(f"  - {needs_search_path}")


if __name__ == "__main__":
    main()
