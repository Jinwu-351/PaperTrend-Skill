#!/usr/bin/env python3
"""Stage 1: 需求解析 — 将用户查询转化为结构化检索参数

用法:
    python stage1_demand.py "研究方向" [data_dir] [选项]

选项:
    --mode <bm25|milvus>             检索模式（写入 demand.json.mode）
    --query_terms "a" "b" "c" ...    自定义扩展关键词（5-8 个，经缺口分析）
    --web_summary "文本..."          Claude 网络调研后的领域背景摘要
    --start_date YYYY-MM-DD          起始日期
    --end_date YYYY-MM-DD            结束日期
    --max_results <int>              每源最大结果数

说明:
    Claude Code 应先用 WebSearch 做网络调研，再向用户提问澄清，
    然后将研究结果通过 --web_summary 和 --query_terms 传入本脚本。
    若省略这些参数，脚本将 fallback 到内置模板，但会输出 ⚠️ 质量警告。

示例:
    # Claude 调研后调用（完整参数）
    python stage1_demand.py "hierarchical reinforcement learning" \\
        data/2026-05-27-15-31 \\
        --mode milvus \\
        --query_terms "hierarchical reinforcement learning" "HRL" "option framework" "temporal abstraction" "skill discovery" \\
        --web_summary "HRL 是 RL 的重要分支，通过将任务分解为多层级策略..."

    # 直接运行（fallback 到内置模板，质量较低）
    python stage1_demand.py "大语言模型推理" --mode bm25
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# 将 lib 目录加入路径
script_dir = Path(__file__).resolve().parent
lib_dir = script_dir.parent / "lib"
sys.path.insert(0, str(lib_dir))

from paper_search import expand_query_terms, generate_web_summary


def get_data_dir(base: Path = None) -> Path:
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d-%H-%M")
    d = (base or Path(".")) / "data" / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


def _skip_flag_and_value(flag):
    """从 argv 中跳过 flag 及其值（不修改原列表）。"""
    idx = sys.argv.index(flag)
    return (idx + 2 < len(sys.argv))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    query = sys.argv[1]

    # --- 提取所有 --flag value 参数 ---
    def flag_value(name, default=None):
        if name in sys.argv:
            idx = sys.argv.index(name)
            if idx + 1 < len(sys.argv):
                return sys.argv[idx + 1]
        return default

    # --query_terms 支持多值: --query_terms "a" "b" "c"
    # 收集 --query_terms 之后所有不以 -- 开头的连续参数
    def flag_list(name):
        if name not in sys.argv:
            return []
        idx = sys.argv.index(name)
        vals = []
        for a in sys.argv[idx + 1:]:
            if a.startswith("--"):
                break
            vals.append(a)
        return vals

    # --confirm 标记：用户确认后将 user_confirmed 设为 true
    user_confirmed = "--confirm" in sys.argv

    mode_raw = flag_value("--mode")
    if mode_raw:
        mode = mode_raw.strip().lower()
        if mode not in ("bm25", "milvus"):
            print(f"警告: --mode 取值非法 ({mode})，将使用默认 bm25")
            mode = "bm25"
    else:
        mode = "bm25"

    query_terms = flag_list("--query_terms")
    web_summary = flag_value("--web_summary")
    start_date = flag_value("--start_date")
    end_date = flag_value("--end_date")
    max_results = int(flag_value("--max_results", "25"))

    # --- Fallback 逻辑：模板兜底 + 质量警告 ---
    now = datetime.now()
    two_years_ago = now.replace(year=now.year - 2)

    if start_date is None:
        start_date = two_years_ago.strftime("%Y-%m-%d")
    if end_date is None:
        end_date = now.strftime("%Y-%m-%d")

    used_fallback = False
    if not query_terms:
        query_terms = expand_query_terms(query)
        print(f"  ⚠️ [fallback] 未传入 --query_terms，使用内置模板生成")
        used_fallback = True

    if not web_summary:
        web_summary = generate_web_summary(query)
        print(f"  ⚠️ [fallback] 未传入 --web_summary，使用内置模板生成")
        print(f"  ⚠️ 建议：Claude Code 应先用 WebSearch 调研后再调用本脚本")
        used_fallback = True

    if used_fallback:
        print(f"\n  ⚠️ 质量警告：本次使用了内置模板，搜索和报告质量可能下降。")
        print(f"  推荐流程：WebSearch → 用户澄清 → 缺口分析 → 传入完整参数\n")

    # --- data_dir: 第一个不以 -- 开头的参数 ---
    skip_flags = {"--mode", "--query_terms", "--web_summary", "--start_date", "--end_date", "--max_results", "--confirm"}
    data_dir = None
    for i, a in enumerate(sys.argv[2:], 2):
        if a.startswith("--"):
            if a in skip_flags:
                continue
            continue
        data_dir = Path(a)
        break
    if data_dir is None:
        data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    demand = {
        "task": f"分析 {query} 的趋势",
        "query": query,
        "query_terms": query_terms,
        "mode": mode,
        "max_results": max_results,
        "authors": None,
        "start_date": start_date,
        "end_date": end_date,
        "categories": None,
        "sort_by": "relevance",
        "web_summary": web_summary,
        "user_confirmed": user_confirmed,
    }

    demand_path = data_dir / "demand.json"
    with open(demand_path, 'w', encoding='utf-8') as f:
        json.dump(demand, f, indent=2, ensure_ascii=False)

    print(f"Stage 1 完成: {demand_path}")
    print(f"  查询: {query}")
    print(f"  扩展词 ({len(query_terms)}): {query_terms}")
    print(f"  模式: {mode}  (后续 Stage 3/4/5 将默认使用该模式)")
    print(f"  时间范围: {demand['start_date']} 至 {demand['end_date']}")
    print(f"  web_summary 长度: {len(web_summary)} 字符")


if __name__ == "__main__":
    main()
