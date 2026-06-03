#!/usr/bin/env python3
"""Stage 6: 构建报告 Prompt

用法:
    python stage6_build_prompt.py <data_dir>

说明:
    - 读取 core_papers.json + supplement_papers.json + demand.json
    - 构建趋势报告 Prompt
    - 输出 report_prompt.md
"""

import sys
import json
from pathlib import Path

script_dir = Path(__file__).resolve().parent
lib_dir = script_dir.parent / "lib"
sys.path.insert(0, str(lib_dir))

from report_builder import build_trend_prompt
from _guard import check_user_confirmed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    data_dir = Path(sys.argv[1])

    # 🛑 守卫检查：确认 Stage 1 已被用户确认
    check_user_confirmed(data_dir)

    # 读取必要文件
    for fname in ["core_papers.json", "supplement_papers.json", "demand.json"]:
        fpath = data_dir / fname
        if not fpath.exists():
            print(f"错误: 未找到 {fpath}")
            sys.exit(1)

    with open(data_dir / "core_papers.json", 'r', encoding='utf-8') as f:
        core_papers = json.load(f)
    with open(data_dir / "supplement_papers.json", 'r', encoding='utf-8') as f:
        supplement_papers = json.load(f)
    with open(data_dir / "demand.json", 'r', encoding='utf-8') as f:
        demand = json.load(f)

    user_query = demand.get("query", "")
    total = len(core_papers) + len(supplement_papers)

    print(f"Stage 6: 构建报告 Prompt")
    print(f"  查询: {user_query}")
    print(f"  论文总数: {total} (核心 {len(core_papers)} + 补充 {len(supplement_papers)})")

    prompt = build_trend_prompt(
        user_query=user_query,
        core_papers=core_papers,
        supplement_papers=supplement_papers,
        demand=demand,
    )

    prompt_path = data_dir / "report_prompt.md"
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"\nStage 6 完成: {prompt_path}")
    print(f"  Prompt 长度: {len(prompt)} 字符")
    print(f"\n下一步: 根据 prompt 撰写趋势分析报告，保存为 report_draft.md")
    print(f"  然后运行: python scripts/save_report.py {data_dir} <report_draft.md>")


if __name__ == "__main__":
    main()
