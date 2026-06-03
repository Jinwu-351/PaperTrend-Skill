#!/usr/bin/env python3
"""共享守卫模块 — 防止 Claude Code 跳过人机交互检查点

在 Stage 2 及之后的脚本开头调用：
    from _guard import check_user_confirmed
    check_user_confirmed(data_dir)

如果 demand.json 中 user_confirmed != True，脚本将拒绝执行。
"""

import json
import sys
from pathlib import Path


def check_user_confirmed(data_dir: Path):
    """检查 Stage 1 的 demand.json 是否已被用户确认。

    未确认时打印错误信息并 sys.exit(1)，强制 Claude Code 停止。
    """
    demand_path = data_dir / "demand.json"
    if not demand_path.exists():
        print(f"\n{'='*60}")
        print(f"🛑 GUARD BLOCKED: 未找到 {demand_path}")
        print(f"   请先运行 Stage 1 生成需求文件。")
        print(f"{'='*60}\n")
        sys.exit(1)

    with open(demand_path, 'r', encoding='utf-8') as f:
        demand = json.load(f)

    confirmed = demand.get("user_confirmed", False)

    if confirmed is not True:
        print(f"\n{'='*60}")
        print(f"🛑 GUARD BLOCKED: Stage 1 demand.json 尚未被用户确认！")
        print(f"{'='*60}")
        print(f"  Claude Code 必须执行以下操作：")
        print(f"  1. 向用户展示 demand.json 的内容")
        print(f"  2. 等待用户回复「继续」或「confirm」")
        print(f"  3. 将 demand.json 中 user_confirmed 设为 true:")
        print(f"       python scripts/stage1_demand.py ... --confirm")
        print(f"       或手动编辑 demand.json 设置 user_confirmed = true")
        print(f"  4. 然后才能重新运行 Stage 2+")
        print(f"{'='*60}\n")
        sys.exit(1)

    # 通过校验，静默继续
    return True