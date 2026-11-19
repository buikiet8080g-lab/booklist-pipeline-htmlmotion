#!/usr/bin/env python3
"""一条命令跑完整条流水线：文案（+ 一张真实封面）→ 成片。

  python3 ours/run_all.py --script 02-final-script.md --cover images/cover-verified.jpg \
      --account accounts/family-education-parent-reader.md --theme wood

做的事（每步失败即停，不产出半成品）：
  04 配音（已有 audio/main-voice.wav 且没有 --redo-audio 就跳过）
  05 分镜（--book auto 从《书名》推；也可 --book metadata/book-assets.json）
  lint 闸门（静态 + 动态抽帧；红灯停）
  07 渲染（并发 + 签名复用）
  08 混音 + ASS 字幕 + QC
最后写 metadata/pipeline-run.json（每步耗时/结论），人只需要看一行「成片 → 路径」。

前置只有两个（其余全自动）：
  1) 02-final-script.md —— 纯正文
  2) 一张真实核验的书封 —— 书单号的书封是转化资产，缺它必须阻塞（D16），不给「无封面出片」的口子
"""
from __future__ import annotations

import argparse, json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def die(msg: str) -> "SystemExit":
    raise SystemExit(f"✗ {msg}")


def run(name: str, cmd: list[str], log: list[dict]) -> None:
    print(f"\n▶ {name}\n  $ {' '.join(str(c) for c in cmd)}", flush=True)
    t0 = time.time()
    r = subprocess.run([str(c) for c in cmd], text=True)
    ok = r.returncode == 0
    log.append({"stage": name, "seconds": round(time.time() - t0, 1), "ok": ok, "cmd": " ".join(str(c) for c in cmd)})
    if not ok:
        die(f"{name} 失败（退出码 {r.returncode}）——修完重跑这一条命令即可，已完成的步骤会跳过")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="02-final-script.md")
    ap.add_argument("--cover", default="", help="书封路径；不写且 --book 是书名 → 自动搜（ours/fetch_cover.py）")
    ap.add_argument("--book", default="", help="书名（自动搜封面）或 metadata/book-assets.json 路径")
    ap.add_argument("--author", default="")
    ap.add_argument("--sources", nargs="*", help="原始文案（1–N 篇）；没有 02-final-script.md 时自动整合改写")
    ap.add_argument("--target-seconds", type=float, default=90, help="目标成片秒数（决定改写字数，默认 90）")
    ap.add_argument("--account", help="账号 md（决定色板/音色/字幕样式）")
    ap.add_argument("--theme", default="", help="色板；不写则按账号的 visual_style_profile.palette")
    ap.add_argument("--title", help="覆盖书名（默认从文案《…》推）")
    ap.add_argument("--sheet", help="可选：按顺序覆盖每镜文案/版式")
    ap.add_argument("--voice", help="覆盖音色")
    ap.add_argument("--captions", help="可选：ASR 校对后的字幕 JSON；不写用分镜边界")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--redo-audio", action="store_true")
    ap.add_argument("--skip-audit", action="store_true", help="跳过 03 内容审核（不建议：句长/口语/覆盖率会没人管）")
    ap.add_argument("--min-coverage", type=float, default=0.55, help="03 覆盖率下限（默认 55%%）")
    ap.add_argument("--force-render", action="store_true")
    a = ap.parse_args()

    ws = Path.cwd()
    if not a.book:
        die("--book 必填：直接给书名（会自动搜封面），或给 metadata/book-assets.json")
    log: list[dict] = []

    # 01 书封：给了文件就用；只给书名就自动搜（豆瓣/OpenLibrary，校验尺寸与书名后落盘）
    book_arg, cover = a.book, a.cover
    if not Path(book_arg).exists():
        if not cover:
            cmd = [PY, ROOT / "ours" / "fetch_cover.py", "--book", book_arg]
            if a.author:
                cmd += ["--author", a.author]
            run("01 书封", cmd, log)
            cover = "images/cover-verified.jpg"
        src = Path("metadata/cover-source.json")
        meta = json.loads(src.read_text(encoding="utf-8")) if src.exists() else {}
        book = {"title": book_arg, "author": a.author or meta.get("edition_author", ""),
                "publisher": "", "cover": cover, "cover_verified": True,
                "cover_source": meta.get("cover_source", "manual"),
                "quote_page": "", "tag": ""}
        Path("metadata").mkdir(exist_ok=True)
        Path("metadata/book-assets.json").write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
        book_arg = "metadata/book-assets.json"
    elif cover:
        book = json.loads(Path(book_arg).read_text(encoding="utf-8"))
        book["cover"] = cover
        Path(book_arg).write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")

    # 02 整合改写：没有 02-final-script.md 但有原始文案 → 先整合（有模型时主 Agent 自己改写更好，见 references/02）
    if not (ws / a.script).exists():
        if not a.sources:
            die(f"没有 {a.script}，也没给 --sources：把文案贴进来（主 Agent 落盘到 sources/*.txt）再跑")
        title = json.loads(Path(book_arg).read_text(encoding="utf-8")).get("title", "")
        run("02 整合改写", [PY, ROOT / "ours" / "rewrite_script.py", "--book", title,
                          "--sources", *a.sources, "--target-seconds", a.target_seconds,
                          "--account", a.account or "", "--out", a.script], log)
    theme = a.theme
    if not theme:
        theme = "wood"
        if a.account and Path(a.account).exists():
            import re
            m = re.search(r"palette:\s*([a-z]+)", Path(a.account).read_text(encoding="utf-8"))
            if m:
                theme = m.group(1)
    audio = ws / "audio" / "main-voice.wav"

    # 03 内容审核（口播性 + 对原稿的覆盖率）：红灯回 02 改稿，不进配音
    if not a.skip_audit:
        cmd = [PY, ROOT / "ours" / "audit_script.py", "--script", a.script,
               "--book", json.loads(Path(book_arg).read_text(encoding="utf-8")).get("title", ""),
               "--out", "03-script-audit.md", "--json", "metadata/03-script-audit.json",
               "--min-coverage", a.min_coverage]
        if a.sources:
            cmd += ["--sources", *a.sources]
        run("03 内容审核", cmd, log)
    else:
        print("· 03 内容审核：已按 --skip-audit 跳过", file=sys.stderr)

    # 04 配音
    if a.redo_audio or not audio.exists():
        cmd = [PY, ROOT / "ours" / "tts_mimo.py", "--script", a.script, "--out", str(audio)]
        if a.account:
            cmd += ["--account", a.account]
        if a.voice:
            cmd += ["--voice", a.voice]
        run("04 配音", cmd, log)
    else:
        print(f"· 04 配音：已有 {audio}（--redo-audio 可重做）")
        log.append({"stage": "04 配音", "seconds": 0, "ok": True, "skipped": True})

    # 05 分镜
    cmd = [PY, ROOT / "ours" / "shot_plan.py", "--script", a.script, "--audio", str(audio),
           "--book", book_arg, "--theme", theme, "--out", "metadata/plan.json", "--markdown", "05-shot-plan.md"]
    if a.title:
        cmd += ["--title", a.title]
    if a.author:
        cmd += ["--author", a.author]
    if a.sheet:
        cmd += ["--sheet", a.sheet]
    if a.account:
        cmd += ["--account", a.account]
    run("05 分镜", cmd, log)

    # 05 闸门
    run("lint 闸门", [PY, ROOT / "ours" / "lint_spec.py", "metadata/plan.json"], log)

    # 07 渲染
    cmd = [PY, ROOT / "ours" / "render_batch.py", "metadata/plan.json", "--workspace", ".", "--parallel", a.parallel]
    if a.force_render:
        cmd.append("--force")
    run("07 渲染", cmd, log)

    # 08a 字幕对齐：默认按语音停顿对齐（不用传参，也不用 key）
    caps = a.captions
    if not caps:
        run("08a 字幕对齐", [PY, ROOT / "ours" / "align_subtitles.py", "--audio", str(audio),
                          "--script", a.script, "--out", "metadata/captions.json"], log)
        caps = "metadata/captions.json"

    # 08b 收尾
    cmd = [PY, ROOT / "ours" / "assemble.py", "metadata/plan.json", "--workspace", ".",
           "--video", "render/master-noaudio.mp4", "--audio", str(audio), "--captions", caps]
    if a.account:
        cmd += ["--account", a.account]
    run("08 收尾", cmd, log)

    final = sorted((ws / "final").glob("*.mp4"))
    if not final:
        die("没有产出 final/*.mp4")
    (ws / "metadata" / "pipeline-run.json").write_text(json.dumps(
        {"pipeline": "booklist-pipeline-htmlmotion", "theme": theme, "account": a.account or "",
         "script": a.script, "cover": a.cover or "", "stages": log,
         "final": str(final[0]), "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
        ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(x["seconds"] for x in log)
    print(f"\n✓ 成片 → {final[0]}")
    detail = " / ".join("%s %.0fs" % (x["stage"], x["seconds"]) for x in log)
    print(f"✓ 全链路 {total:.0f}s（{detail}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
