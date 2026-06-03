#!/usr/bin/env python3
"""Stage 5: 补充论文 RRF 检索

用法:
    python stage5_supplement.py <data_dir> [--top_k 50] [--mode bm25|milvus]

说明:
    - 从 abstracts.json 加载摘要
    - 根据 demand.json 中的 query_terms 进行多关键词检索
    - 排除 core_papers.json 中的核心论文
    - mode 解析优先级: CLI --mode > demand.json.mode > "bm25"
    - 输出 supplement_papers.json
"""

import sys
import json
from pathlib import Path

script_dir = Path(__file__).resolve().parent
lib_dir = script_dir.parent / "lib"
sys.path.insert(0, str(lib_dir))
sys.path.insert(0, str(script_dir))

from paper_retrieval import AbstractStore, BM25Retriever
from paper_search import normalize_title
from _mode_resolver import resolve_mode
from _guard import check_user_confirmed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    data_dir = Path(sys.argv[1])

    # 🛑 守卫检查：确认 Stage 1 已被用户确认
    check_user_confirmed(data_dir)

    top_k = 50
    if "--top_k" in sys.argv:
        idx = sys.argv.index("--top_k")
        if idx + 1 < len(sys.argv):
            top_k = int(sys.argv[idx + 1])

    mode = resolve_mode(sys.argv, data_dir)

    # 读取 demand.json 获取 query_terms
    demand_path = data_dir / "demand.json"
    if not demand_path.exists():
        print(f"错误: 未找到 {demand_path}，请先运行 Stage 1")
        sys.exit(1)

    with open(demand_path, 'r', encoding='utf-8') as f:
        demand = json.load(f)

    query_terms = demand.get("query_terms", [demand.get("query", "")])

    # 读取 core_papers.json 用于排除
    core_path = data_dir / "core_papers.json"
    if not core_path.exists():
        print(f"错误: 未找到 {core_path}，请先运行 Stage 4")
        sys.exit(1)

    with open(core_path, 'r', encoding='utf-8') as f:
        core_papers = json.load(f)

    exclude_titles = set()
    for p in core_papers:
        nt = normalize_title(p.get("title", ""))
        if nt:
            exclude_titles.add(nt)

    # 检查 abstracts.json
    abstracts_path = data_dir / "abstracts.json"
    if not abstracts_path.exists():
        print(f"错误: 未找到 {abstracts_path}，请先运行 Stage 3")
        sys.exit(1)

    print(f"Stage 5: 补充论文 RRF 检索 (terms={len(query_terms)}, top_k={top_k})")

    if mode == "milvus":
        from paper_retrieval import MilvusStore
        store = MilvusStore(data_dir)
        store.load()
        supplement_papers = store.search_multi_rrf(
            queries=query_terms, top_k=top_k, exclude_titles=exclude_titles,
        )
    else:
        store = AbstractStore(data_dir)
        store.load()
        retriever = BM25Retriever()
        retriever.build_index(store.all_papers())
        supplement_papers = retriever.search_multi_rrf(
            queries=query_terms, top_k=top_k, exclude_titles=exclude_titles,
        )

    supplement_path = data_dir / "supplement_papers.json"
    with open(supplement_path, 'w', encoding='utf-8') as f:
        json.dump(supplement_papers, f, indent=2, ensure_ascii=False)

    print(f"\nStage 5 完成: {supplement_path}")
    print(f"  补充论文: {len(supplement_papers)} 篇")


if __name__ == "__main__":
    main()
