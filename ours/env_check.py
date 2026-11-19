#!/usr/bin/env python3
"""环境自检（T20）：node/ffmpeg/playwright/vendor 基线/中文字体/补丁状态，一条命令跑完。"""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "huashu-art-motion"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main() -> int:
    checks = []
    py = sys.version.split()[0]
    checks.append(("python ≥3.10", tuple(map(int, py.split(".")[:2])) >= (3, 10), py))
    checks.append(("ffmpeg", shutil.which("ffmpeg") is not None, (run(["ffmpeg", "-version"]).stdout.splitlines() or [""])[0][:40]))
    checks.append(("ffprobe", shutil.which("ffprobe") is not None, "ok"))
    try:
        import playwright  # noqa: F401
        import importlib.metadata as md
        checks.append(("playwright", True, md.version("playwright")))
    except Exception:                                        # noqa: BLE001
        checks.append(("playwright", False, "pip install playwright"))
    try:
        from PIL import Image  # noqa: F401
        checks.append(("Pillow", True, "ok"))
    except Exception:                                        # noqa: BLE001
        checks.append(("Pillow", False, "pip install pillow"))
    # 浏览器缓存
    cache = Path.home() / ".cache" / "ms-playwright"
    got = sorted(p.name for p in cache.glob("chromium_headless_shell-*")) + sorted(p.name for p in cache.glob("chromium-*"))
    checks.append(("chromium 缓存", bool(got), ", ".join(got[:4]) or f"playwright install chromium（{cache}）"))
    # vendor 基线
    if (VENDOR / ".git").exists():
        tag = run(["git", "describe", "--tags"], cwd=VENDOR).stdout.strip()
        st = run(["git", "status", "--porcelain"], cwd=VENDOR).stdout.strip().splitlines()
        checks.append(("vendor tag = v1.2.0", tag == "v1.2.0", tag or "?"))
        checks.append(("vendor 改动只来自 patches", len(st) <= 11, f"{len(st)} 个文件被改（0=未 apply；11=6 个 patch 全 apply）"))
    else:
        checks.append(("vendor 是 git 工作树", False, "见 vendor/BASELINE.md 离线副本做法"))
    eng = VENDOR / "scripts" / "engine"
    size = sum(p.stat().st_size for p in eng.rglob("*") if p.is_file()) / 1e6 if eng.exists() else 0
    checks.append(("scripts/engine ≈24M", 20 <= size <= 30, f"{size:.0f}M"))
    fonts = list((eng / "lib" / "fonts").glob("NotoSansSC-*.woff"))
    checks.append(("中文字体在位", len(fonts) >= 4, f"{len(fonts)} 个字重 + NotoSerifSC/LXGWWenKai"))
    zh = run(["fc-list", ":lang=zh"]).stdout.strip().splitlines()
    checks.append(("系统中文字体", len(zh) >= 1, f"{len(zh)} 条（字幕烧录用 WenQuanYi Zen Hei）"))
    for name, ok, detail in checks:
        print(f"{'✓' if ok else '✗'} {name}：{detail}")
    bad = [c for c in checks if not c[1]]
    print(f"{'✓' if not bad else '✗'} env_check：{len(checks)-len(bad)}/{len(checks)} 通过")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
