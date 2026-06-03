#!/usr/bin/env python3
"""Stage 0: 模式探测 — 检测环境并推荐 BM25 / Milvus 模式

用法:
    python stage0_mode.py [--data_dir <data_dir>] [--json]

说明:
    - 探测 pymilvus、sentence-transformers 是否安装
    - 探测 Milvus 本地数据库是否存在
    - 输出可读报告（默认）或 JSON（--json）
    - 不写入任何文件，仅供 Claude 读取后与用户确认模式

输出 JSON 结构:
    {
      "available": ["bm25", "milvus"],          # 当前环境可用的模式
      "recommended": "milvus",                   # 推荐模式
      "reasons": {                               # 推荐原因 / 各模式状态
        "bm25":   {"ready": true,  "note": "..."},
        "milvus": {"ready": true,  "note": "...", "existing_collections": [...]}
      },
      "checks": {                                # 详细环境检测
        "pymilvus": true,
        "sentence_transformers": true,
        "milvus_db_path": "milvus_data/milvus_data.db",
        "milvus_db_exists": true
      }
    }
"""

import sys
import json
import importlib.util
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def detect_environment(project_root: Path):
    checks = {
        "pymilvus": has_module("pymilvus"),
        "sentence_transformers": has_module("sentence_transformers"),
    }

    # Milvus 本地数据库探测（Milvus Lite 单文件）
    candidate_paths = [
        project_root / "milvus_data" / "milvus_data.db",
        project_root / "milvus_data.db",
    ]
    db_path = None
    db_exists = False
    for p in candidate_paths:
        if p.exists():
            db_path = p
            db_exists = True
            break
    if db_path is None:
        db_path = candidate_paths[0]

    checks["milvus_db_path"] = str(db_path)
    checks["milvus_db_exists"] = db_exists

    # 已有 collections 列表（如果可读）
    existing_collections = []
    if db_exists:
        coll_dir = db_path / "collections" if db_path.is_dir() else None
        # Milvus Lite 把 collections 当目录处理；做一个兼容尝试
        try:
            if coll_dir and coll_dir.exists():
                existing_collections = sorted([c.name for c in coll_dir.iterdir() if c.is_dir()])
        except Exception:
            pass

    return checks, existing_collections


def decide(checks, existing_collections):
    bm25_ready = True  # 始终可用
    milvus_ready = checks["pymilvus"] and checks["sentence_transformers"]

    available = ["bm25"]
    reasons = {
        "bm25": {"ready": True, "note": "零依赖，关键词 BM25 匹配，毫秒级"},
    }
    if milvus_ready:
        available.append("milvus")
        note = "向量语义检索 (BGE embedding + 余弦相似度)"
        if existing_collections:
            note += f"，检测到已有 collection: {existing_collections}"
        reasons["milvus"] = {
            "ready": True,
            "note": note,
            "existing_collections": existing_collections,
        }
    else:
        missing = []
        if not checks["pymilvus"]:
            missing.append("pymilvus")
        if not checks["sentence_transformers"]:
            missing.append("sentence-transformers")
        reasons["milvus"] = {
            "ready": False,
            "note": f"缺少依赖: {', '.join(missing)}，可执行: pip install {' '.join(missing)}",
            "existing_collections": existing_collections,
        }

    # 推荐策略：
    # - 若 Milvus 可用且已有 collection（可复用历史向量）→ 推荐 Milvus
    # - 否则若 Milvus 可用 → 仍推荐 Milvus（语义检索质量更好），但用户可选 BM25
    # - 否则 → 推荐 BM25
    if milvus_ready and existing_collections:
        recommended = "milvus"
    elif milvus_ready:
        recommended = "milvus"
    else:
        recommended = "bm25"

    return available, recommended, reasons


def print_human_report(result):
    print("=" * 60)
    print("Stage 0: 环境探测 & 模式推荐")
    print("=" * 60)
    c = result["checks"]
    print("\n[环境检测]")
    print(f"  pymilvus              : {'✓' if c['pymilvus'] else '✗'}")
    print(f"  sentence-transformers : {'✓' if c['sentence_transformers'] else '✗'}")
    print(f"  Milvus DB 路径        : {c['milvus_db_path']}")
    print(f"  Milvus DB 存在        : {'✓' if c['milvus_db_exists'] else '✗'}")

    print("\n[可用模式]")
    for m in ["bm25", "milvus"]:
        r = result["reasons"][m]
        flag = "✓" if r["ready"] else "✗"
        print(f"  [{flag}] {m:<7} — {r['note']}")
        if m == "milvus" and r.get("existing_collections"):
            print(f"        已有 collections: {r['existing_collections']}")

    print(f"\n💡 推荐模式: {result['recommended']}")
    print("\n请向用户确认模式后，使用以下命令进入 Stage 1:")
    print(f"  python academic-trend-analysis/scripts/stage1_demand.py \"<query>\" <data_dir> --mode {result['recommended']}")
    print("=" * 60)


def main():
    project_root = Path.cwd()
    as_json = "--json" in sys.argv

    # 允许指定 data_dir 仅用于显示；本 stage 不写文件
    data_dir = None
    if "--data_dir" in sys.argv:
        idx = sys.argv.index("--data_dir")
        if idx + 1 < len(sys.argv):
            data_dir = Path(sys.argv[idx + 1])

    checks, existing_collections = detect_environment(project_root)
    available, recommended, reasons = decide(checks, existing_collections)

    result = {
        "available": available,
        "recommended": recommended,
        "reasons": reasons,
        "checks": checks,
    }
    if data_dir:
        result["data_dir_hint"] = str(data_dir)

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human_report(result)


if __name__ == "__main__":
    main()
