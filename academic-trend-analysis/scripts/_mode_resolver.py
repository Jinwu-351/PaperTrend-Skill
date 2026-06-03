"""共享 mode 解析逻辑：
优先级：CLI --mode > demand.json.mode > "bm25"
打印解析来源便于调试。
"""

import json
import sys
from pathlib import Path


VALID_MODES = ("bm25", "milvus")


def _parse_cli_mode(argv):
    if "--mode" in argv:
        idx = argv.index("--mode")
        if idx + 1 < len(argv):
            m = argv[idx + 1].strip().lower()
            if m in VALID_MODES:
                return m
            print(f"[mode resolution] 警告: --mode 值非法 ({m})，已忽略", file=sys.stderr)
    return None


def _parse_demand_mode(data_dir: Path):
    demand_path = Path(data_dir) / "demand.json"
    if not demand_path.exists():
        return None
    try:
        with open(demand_path, "r", encoding="utf-8") as f:
            demand = json.load(f)
        m = (demand.get("mode") or "").strip().lower()
        if m in VALID_MODES:
            return m
    except Exception as e:
        print(f"[mode resolution] 读取 demand.json 失败: {e}", file=sys.stderr)
    return None


def resolve_mode(argv, data_dir, default="bm25", verbose=True):
    """按优先级解析检索模式。"""
    m = _parse_cli_mode(argv)
    if m:
        if verbose:
            print(f"[mode resolution] source=CLI value={m}")
        return m

    m = _parse_demand_mode(data_dir)
    if m:
        if verbose:
            print(f"[mode resolution] source=demand.json value={m}")
        return m

    if verbose:
        print(f"[mode resolution] source=default value={default}")
    return default
