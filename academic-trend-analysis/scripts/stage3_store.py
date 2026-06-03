#!/usr/bin/env python3
"""Stage 3: 摘要入库

用法:
    python stage3_store.py <data_dir> [--mode bm25|milvus]

说明:
    - 从 paper_pre_list.json 读取论文
    - 摘要存储为 abstracts.json
    - mode 解析优先级: CLI --mode > demand.json.mode > "bm25"
    - --mode milvus 使用 Milvus 向量存储（需额外依赖）
"""

import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
lib_dir = script_dir.parent / "lib"
sys.path.insert(0, str(lib_dir))
sys.path.insert(0, str(script_dir))

from paper_search import load_papers
from _mode_resolver import resolve_mode
from _guard import check_user_confirmed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    data_dir = Path(sys.argv[1])

    # 🛑 守卫检查：确认 Stage 1 已被用户确认
    check_user_confirmed(data_dir)

    mode = resolve_mode(sys.argv, data_dir)

    pre_list_path = data_dir / "paper_pre_list.json"
    if not pre_list_path.exists():
        print(f"错误: 未找到 {pre_list_path}，请先运行 Stage 2")
        sys.exit(1)

    papers = load_papers(data_dir)
    if not papers:
        print("错误: paper_pre_list.json 为空")
        sys.exit(1)

    print(f"Stage 3: 摘要入库 (mode={mode})")
    print(f"  待入库论文: {len(papers)} 篇")

    if mode == "milvus":
        from paper_retrieval import MilvusStore
        store = MilvusStore(data_dir)
        store.load()
        new_count, skip_count = store.add_batch(papers)
        store.save()
        print(f"  Milvus 入库: 新增 {new_count} 篇，跳过 {skip_count} 篇")
        print(f"  Milvus 总计: {store.count()} 篇")
    else:
        from paper_retrieval import AbstractStore
        store = AbstractStore(data_dir)
        store.load()
        new_count, skip_count = store.add_batch(papers)
        store.save()
        print(f"  新增 {new_count} 篇，跳过 {skip_count} 篇")
        print(f"  总计: {store.count()} 篇")

    print(f"\nStage 3 完成: {data_dir / 'abstracts.json'}")


if __name__ == "__main__":
    main()
