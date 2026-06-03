#!/usr/bin/env python3
"""Stage 2: 多源论文搜索 + 去重

用法:
    python stage2_search.py <data_dir> [--max_results 25]

说明:
    - 从 data_dir/demand.json 读取 query_terms
    - 搜索 arXiv + Semantic Scholar + OpenAlex + AlphaXiv
    - 去重后保存为 paper_pre_list.json
"""

import sys
import json
from pathlib import Path

script_dir = Path(__file__).resolve().parent
lib_dir = script_dir.parent / "lib"
sys.path.insert(0, str(lib_dir))

from paper_search import search_multi, save_papers
from _guard import check_user_confirmed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    data_dir = Path(sys.argv[1])

    # 🛑 守卫检查：确认 Stage 1 已被用户确认
    check_user_confirmed(data_dir)

    max_results = 25
    if "--max_results" in sys.argv:
        idx = sys.argv.index("--max_results")
        if idx + 1 < len(sys.argv):
            max_results = int(sys.argv[idx + 1])

    # 读取 demand.json
    demand_path = data_dir / "demand.json"
    if not demand_path.exists():
        print(f"错误: 未找到 {demand_path}，请先运行 Stage 1")
        sys.exit(1)

    with open(demand_path, 'r', encoding='utf-8') as f:
        demand = json.load(f)

    query_terms = demand.get("query_terms", [demand.get("query", "")])
    year_range = None
    start = demand.get("start_date", "")
    end = demand.get("end_date", "")
    if start and end:
        year_range = (int(start[:4]), int(end[:4]))

    print(f"Stage 2: 论文搜索")
    print(f"  关键词: {query_terms}")
    print(f"  每源最大: {max_results}")
    if year_range:
        print(f"  时间范围: {year_range[0]}-{year_range[1]}")

    all_papers, deduped_papers, reports = search_multi(
        queries=query_terms, max_results=max_results, year_range=year_range,
    )

    for r in reports:
        print(f"  {r}")

    save_papers(data_dir, deduped_papers)

    print(f"\nStage 2 完成: {data_dir / 'paper_pre_list.json'}")
    print(f"  搜索总计: {len(all_papers)} 篇")
    print(f"  去重后: {len(deduped_papers)} 篇")


if __name__ == "__main__":
    main()
