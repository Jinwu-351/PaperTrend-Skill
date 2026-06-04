#!/usr/bin/env python3
"""
跨平台一键部署 academic-trend-analysis 到 Claude Code 和 Codex 的 Skills 目录。

用法:
    python deploy.py --global    # 全局部署到 ~/.claude/skills/ 和 ~/.codex/skills/
    python deploy.py --local     # 项目级部署到当前项目的 .claude/skills/ 和 .codex/skills/
    python deploy.py --remove    # 卸载全局和项目级链接
    python deploy.py --dry-run   # 预览操作，不实际执行

平台适配:
    Linux / macOS:  符号链接 (os.symlink)
    Windows:        目录连接 (mklink /J)，无需管理员权限
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def is_windows():
    return platform.system() == "Windows"


def create_link(src, dst, dry_run=False):
    """创建跨平台目录链接。

    Unix:  os.symlink(src, dst)
    Windows: mklink /J dst src (junction point)
    """
    src = str(src.resolve())
    dst_dir = dst.parent

    if dry_run:
        print(f"  [DRY-RUN] 创建链接: {dst} -> {src}")
        return True

    dst_dir.mkdir(parents=True, exist_ok=True)

    if is_windows():
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dst), src],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  失败: {result.stderr.strip()}")
            return False
    else:
        try:
            os.symlink(src, dst)
        except FileExistsError:
            if dst.is_symlink() and str(dst.resolve()) == src:
                print(f"  已存在（跳过）: {dst}")
                return True
            if dst.is_dir() and not dst.is_symlink():
                print(f"  失败: {dst} 已存在且不是链接")
                return False
            os.remove(dst)
            os.symlink(src, dst)

    print(f"  已创建: {dst} -> {src}")
    return True


def remove_link(path, dry_run=False):
    """安全删除链接，绝不删除源目录。

    Unix:  os.unlink(path) 或 os.remove(path)
    Windows: cmd rmdir /Q path (仅删除 junction point)
    """
    if not path.exists() and not path.is_symlink():
        print(f"  不存在（跳过）: {path}")
        return True

    # 安全保护：如果是真实目录（非链接），拒绝删除
    if path.is_dir() and not path.is_symlink():
        if not is_windows():
            print(f"  拒绝删除: {path} 是真实目录，不是链接")
            return False
        # Windows 下 junction 的 Path.is_dir() 返回 True 但 Path.is_symlink() 也返回 True
        # 如果走到这里 is_symlink() 为 False，说明不是 junction

    if dry_run:
        print(f"  [DRY-RUN] 删除链接: {path}")
        return True

    if is_windows():
        result = subprocess.run(
            ["cmd", "/c", "rmdir", "/Q", str(path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  失败: {result.stderr.strip()}")
            return False
    else:
        os.unlink(path)

    print(f"  已删除: {path}")
    return True


def get_global_paths():
    """获取全局部署目标路径。"""
    home = Path.home()

    claude_path = home / ".claude" / "skills" / "academic-trend-analysis"

    # Codex 优先使用 CODEX_HOME
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        codex_path = Path(codex_home) / "skills" / "academic-trend-analysis"
    else:
        codex_path = home / ".codex" / "skills" / "academic-trend-analysis"

    return claude_path, codex_path


def get_local_paths():
    """获取项目级部署目标路径。"""
    cwd = Path.cwd()
    return cwd / ".claude" / "skills" / "academic-trend-analysis", \
           cwd / ".codex" / "skills" / "academic-trend-analysis"


def get_source_path():
    """获取源码目录（脚本所在目录下的 academic-trend-analysis/）。"""
    return Path(__file__).resolve().parent / "academic-trend-analysis"


def deploy(global_mode, dry_run=False):
    """执行部署。

    Args:
        global_mode: True=全局, False=项目级
        dry_run: 仅预览
    """
    src = get_source_path()
    if not src.is_dir():
        print(f"错误: 源码目录不存在: {src}")
        return False

    if global_mode:
        targets = list(get_global_paths())
        # 也检查项目级是否已有旧链接需要提示
        local_targets = list(get_local_paths())
    else:
        targets = list(get_local_paths())

    print(f"源码目录: {src}")

    success = True
    for dst in targets:
        if dst.exists() or dst.is_symlink():
            if str(dst.resolve()) == str(src.resolve()):
                print(f"  已存在（跳过）: {dst}")
                continue
            print(f"  已存在不同目标: {dst} -> {dst.resolve()}")
            if not dry_run:
                print(f"  先删除旧链接...")
                if not remove_link(dst, dry_run=False):
                    success = False
                    continue

        if not create_link(src, dst, dry_run=dry_run):
            success = False

    if success and not dry_run:
        print("\n验证部署...")
        for dst in targets:
            if dst.is_symlink() or (dst.exists() and dst.is_dir()):
                skill_md = dst / "SKILL.md"
                if skill_md.exists():
                    print(f"  OK: {dst}/SKILL.md 可访问")
                else:
                    print(f"  警告: {dst}/SKILL.md 不存在")
                    success = False
            else:
                print(f"  警告: {dst} 未正确创建")
                success = False

    return success


def do_remove(dry_run=False):
    """卸载全局和项目级的链接。"""
    print("卸载所有链接...")

    success = True

    # 全局
    print("  全局 Skills:")
    claude, codex = get_global_paths()
    if not remove_link(claude, dry_run=dry_run):
        success = False
    if not remove_link(codex, dry_run=dry_run):
        success = False

    # 项目级（如果存在）
    local_claude, local_codex = get_local_paths()
    if local_claude.exists() or local_claude.is_symlink():
        print("  项目级 Skills:")
        if not remove_link(local_claude, dry_run=dry_run):
            success = False
        if not remove_link(local_codex, dry_run=dry_run):
            success = False

    return success


def main():
    parser = argparse.ArgumentParser(
        description="部署 academic-trend-analysis 到 Claude Code 和 Codex 的 Skills 目录",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--global", dest="global_mode", action="store_true",
                       help="全局部署到 ~/.claude/skills/ 和 ~/.codex/skills/")
    group.add_argument("--local", dest="local_mode", action="store_true",
                       help="项目级部署到 .claude/skills/ 和 .codex/skills/")
    group.add_argument("--remove", action="store_true",
                       help="卸载全局和项目级链接")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览操作，不实际执行")

    args = parser.parse_args()

    if args.remove:
        ok = do_remove(dry_run=args.dry_run)
    else:
        mode = args.global_mode
        label = "全局" if mode else "项目级"
        print(f"{'[DRY-RUN] ' if args.dry_run else ''}{label}部署:")
        ok = deploy(global_mode=mode, dry_run=args.dry_run)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
