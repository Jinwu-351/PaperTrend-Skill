#!/usr/bin/env python3
"""保存趋势报告 — 自动追加 GB/T 7714 参考文献

用法:
    python save_report.py <data_dir> <report_draft.md>

说明:
    - 读取报告草稿中的所有 [N] 引用
    - 自动重映射为连续编号
    - 从 core_papers.json + supplement_papers.json 生成参考文献
    - 输出最终的 report.md
"""

import sys
from pathlib import Path

# 将 lib 目录加入路径
script_dir = Path(__file__).resolve().parent
lib_dir = script_dir.parent / "lib"
sys.path.insert(0, str(lib_dir))

from report_builder import save_report, validate_citations
from _guard import check_user_confirmed


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    data_dir = Path(sys.argv[1])
    draft_path = Path(sys.argv[2])

    if not draft_path.exists():
        print(f"错误: 报告草稿 {draft_path} 不存在")
        sys.exit(1)

    # 🛑 守卫检查：确认 Stage 1 已被用户确认
    check_user_confirmed(data_dir)

    # 读取报告草稿
    with open(draft_path, 'r', encoding='utf-8') as f:
        report_content = f.read()

    # 读取论文数据
    import json
    all_papers = []

    core_path = data_dir / "core_papers.json"
    supplement_path = data_dir / "supplement_papers.json"

    if core_path.exists():
        with open(core_path, 'r', encoding='utf-8') as f:
            all_papers.extend(json.load(f))
    if supplement_path.exists():
        with open(supplement_path, 'r', encoding='utf-8') as f:
            all_papers.extend(json.load(f))

    if not all_papers:
        print("错误: 没有找到论文数据")
        sys.exit(1)

    # 引用幻觉检测
    print(f"\n{'='*50}")
    print(f"Stage 7.5: 引用验证（Citation Audit）")
    print(f"{'='*50}")
    suspicious = validate_citations(report_content, all_papers)
    if suspicious:
        print(f"\n⚠️  发现 {len(suspicious)} 处可疑引用（正文描述与对应论文内容可能不匹配）：\n")
        for s in suspicious:
            print(f"  [{s['citation_num']}] 正文: ...{s['sentence'][:80]}...")
            print(f"       论文: {s['paper_title'][:80]}")
            print(f"       显著术语: {', '.join(s['significant_terms'])}")
            print(f"       匹配: (无)")
            print(f"       → {s['verdict']}")
            print()
        print(f"  建议: 请手动检查以上引用，确认正文描述与论文内容一致后重新运行。")
    else:
        print(f"\n✅ 未发现可疑引用，所有 [N] 引用与对应论文内容基本匹配。")

    print(f"\n论文总数: {len(all_papers)} 篇 (核心 {len([p for p in all_papers if p.get('score')])} + 补充 {len([p for p in all_papers if 'score' not in p])})")
    print(f"保存报告: {data_dir / 'report.md'}")

    report_path = save_report(data_dir, report_content, all_papers)

    print(f"报告已保存: {report_path}")


if __name__ == "__main__":
    main()
