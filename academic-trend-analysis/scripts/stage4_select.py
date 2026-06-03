#!/usr/bin/env python3
"""Stage 4: 核心论文筛选

用法:
    python stage4_select.py <data_dir> [--limit 12] [--mode bm25|milvus]

说明:
    - 从 abstracts.json 加载摘要
    - 根据 demand.json 中的 query 筛选核心论文
    - mode 解析优先级: CLI --mode > demand.json.mode > "bm25"
    - 输出 core_papers.json
"""

import sys
import json
from pathlib import Path

script_dir = Path(__file__).resolve().parent
lib_dir = script_dir.parent / "lib"
sys.path.insert(0, str(lib_dir))
sys.path.insert(0, str(script_dir))

from paper_retrieval import AbstractStore, select_key_papers
from _mode_resolver import resolve_mode
from _guard import check_user_confirmed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    data_dir = Path(sys.argv[1])

    # 🛑 守卫检查：确认 Stage 1 已被用户确认
    check_user_confirmed(data_dir)

    limit = 12
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    mode = resolve_mode(sys.argv, data_dir)

    # 读取 demand.json 获取 query
    demand_path = data_dir / "demand.json"
    if not demand_path.exists():
        print(f"错误: 未找到 {demand_path}，请先运行 Stage 1")
        sys.exit(1)

    with open(demand_path, 'r', encoding='utf-8') as f:
        demand = json.load(f)

    # 优先使用 query_terms（英文）做 BM25/Milvus 检索
    # 因为论文摘要都是英文，中文 query 无法匹配到任何 token
    query_terms = demand.get("query_terms", [])
    if query_terms and isinstance(query_terms, list) and len(query_terms) > 0:
        query = query_terms[0]  # 第一个英文关键词最通用
    else:
        query = demand.get("query", "")
    if not query:
        print("错误: demand.json 中缺少 query 和 query_terms 字段")
        sys.exit(1)

    # 检查 abstracts.json
    abstracts_path = data_dir / "abstracts.json"
    if not abstracts_path.exists():
        print(f"错误: 未找到 {abstracts_path}，请先运行 Stage 3")
        sys.exit(1)

    print(f"Stage 4: 核心论文筛选 (query='{query[:80]}...', limit={limit})")

    if mode == "milvus":
        from paper_retrieval import MilvusStore
        store = MilvusStore(data_dir)
        store.load()
        core_papers = store.select_key_papers(query, limit=limit)
    else:
        store = AbstractStore(data_dir)
        store.load()
        core_papers = select_key_papers(store, query, limit=limit)

    core_path = data_dir / "core_papers.json"
    with open(core_path, 'w', encoding='utf-8') as f:
        json.dump(core_papers, f, indent=2, ensure_ascii=False)

    print(f"\nStage 4 完成: {core_path}")
    for i, p in enumerate(core_papers, 1):
        score = p.get("score", "?")
        title = p.get("title", p.get("file_name", "?"))[:80]
        print(f"  [{i}] score={score}  {title}")


if __name__ == "__main__":
    main()
