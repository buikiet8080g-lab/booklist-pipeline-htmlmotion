#!/usr/bin/env python3
"""08 收尾：主画面 + 主音轨 + 字幕 → final/发布版.mp4，并做 ffprobe QC。

字幕一律走后期 ASS 烧录（D15）：场景代码里永远不写字幕。字幕样式由账号的 visual_style_profile 决定，
默认 46px / 白字黑描边 / 底部 MarginV=110（落在 980–1280 的字幕安全区里，不进画面正文区）。

用法：
  python3 ours/assemble.py metadata/plan.json --workspace <项目> \
      --video render/master-noaudio.mp4 --audio audio/main-voice.wav \
      [--captions metadata/captions.json] [--account accounts/family-education-parent-reader.md]
字幕来源：--captions 给了就用（groq-subtitle-generator 的产物，或 ASR 后校对的 JSON）；
没有就用 plan.json 每镜的 subtitle_lines + narration_span 生成（样片/质检够用，正式发布要 ASR 对齐）。
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys
from pathlib import Path

SAFE_BOTTOM = 300


def die(msg: str) -> "SystemExit":
    raise SystemExit(f"✗ {msg}")


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=width,height,r_frame_rate,codec_type:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True)
    if out.returncode != 0:
        die(f"ffprobe 打不开 {path}\n{out.stderr.strip()}")
    d = json.loads(out.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), {})
    return {"duration": float(d.get("format", {}).get("duration") or 0), "w": v.get("width"), "h": v.get("height"),
            "fps": v.get("r_frame_rate"), "audio": bool(a)}


MAX_UNITS = 12          # 46px 字在 720 宽画面上，一行最多约 12 个汉字（720−2×56 边距 / 46 ≈ 13）


def wrap_sub(text: str, max_units: int = MAX_UNITS, max_lines: int = 3) -> str:
    """把一条字幕折成 ≤max_lines 行、每行 ≤max_units 汉字宽。优先在标点断，没有标点就硬断。
    不做「超出画面」的事：字幕超出 720 宽就会被边缘切掉（实测 23 字的句子两行以外还溢出）。"""
    text = text.replace("\n", " ")
    lines, rest = [], text
    while rest:
        if len(rest) <= max_units:
            lines.append(rest); break
        seg = rest[:max_units]
        cut = max((seg.rfind(p) for p in "，。；、！？：,"), default=-1)
        if cut >= 5:
            lines.append(rest[:cut + 1]); rest = rest[cut + 1:]
        else:
            lines.append(seg); rest = rest[max_units:]
        if len(lines) >= 4:                    # 四行封顶（底部 300px 放得下 4×52px）；再长就把剩下的一次塞进最后一行
            lines[-1] += rest; rest = ""
    return "\\N".join(x.strip() for x in lines if x.strip())


def ts(x: float) -> str:
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def profile(account: Path | None) -> dict:
    """从账号 md 里读 visual_style_profile.subtitle_style（没有就用默认）。"""
    st = {"font": "WenQuanYi Zen Hei", "size": 46, "margin_v": 110, "outline": 3, "shadow": 0,
          "primary": "&H00FFFFFF", "back": "&H80000000"}
    if account and account.exists():
        txt = account.read_text(encoding="utf-8")
        m = re.search(r"subtitle_style:\s*\n((?:\s+\w+:.*\n)+)", txt)
        if m:
            for ln in m.group(1).splitlines():
                k, _, v = ln.strip().partition(":")
                k, v = k.strip(), v.strip().strip('"')
                if k in ("size", "margin_v", "outline", "shadow") and v.isdigit():
                    st[k] = int(v)
                elif k in ("font", "primary", "back") and v:
                    st[k] = v
    return st


def build_ass(cues: list[dict], st: dict) -> str:
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BL,{st['font']},{st['size']},{st['primary']},&H000000FF,&H00101010,{st['back']},0,0,0,0,100,100,1.5,0,1,{st['outline']},{st['shadow']},2,56,56,{st['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = []
    for c in cues:
        body.append(f"Dialogue: 0,{ts(c['start'])},{ts(c['end'])},BL,,0,0,0,,{wrap_sub(str(c.get('text', '')))}")
    return head + "\n".join(body) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--video", default="render/master-noaudio.mp4")
    ap.add_argument("--audio", default="audio/main-voice.wav")
    ap.add_argument("--captions")
    ap.add_argument("--account")
    ap.add_argument("--out", default="final")
    a = ap.parse_args()
    ws = Path(a.workspace).resolve()
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    video, audio = ws / a.video, ws / a.audio
    for p in (video, audio):
        if not p.exists():
            die(f"缺文件：{p}")
    if a.captions:
        cues = json.loads(Path(a.captions).read_text(encoding="utf-8"))
    else:
        cues = []
        for sh in plan["shots"]:
            s, e = sh["narration_span"]
            for ln in sh.get("subtitle_lines") or []:
                cues.append({"start": s, "end": e, "text": ln})
        print("! 没有 --captions：用 plan.json 的分镜边界当字幕时间（样片可用；正式发布请用 ASR 对齐）", file=sys.stderr)

    st = profile(Path(a.account) if a.account else None)
    outdir = ws / a.out; outdir.mkdir(parents=True, exist_ok=True)
    ass = ws / "metadata" / "subtitles.ass"
    ass.parent.mkdir(parents=True, exist_ok=True)
    ass.write_text(build_ass(cues, st), encoding="utf-8")
    acct = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", str(plan.get("account") or "booklist")).strip("-")
    final = outdir / f"发布版-{acct}-{plan.get('theme','paper')}.mp4"
    vf = f"ass={ass.name}"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(audio),
                    "-vf", vf, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)],
                   check=True, cwd=str(ass.parent))

    fv, fa = probe(final), probe(audio)
    checks = []
    checks.append(("分辨率 720×1280", fv["w"] == 720 and fv["h"] == 1280, f"{fv['w']}×{fv['h']}"))
    checks.append(("帧率 24", fv["fps"] in ("24/1", "24"), str(fv["fps"])))
    checks.append(("有音轨", fv["audio"], "aac"))
    checks.append(("时长对齐 ≤0.5s", abs(fv["duration"] - fa["duration"]) <= 0.5, f"{fv['duration']:.2f}s / 音轨 {fa['duration']:.2f}s"))
    checks.append(("字幕在底部安全区内", st["margin_v"] + st["size"] * 1.35 <= SAFE_BOTTOM + 60, f"MarginV={st['margin_v']} size={st['size']}"))
    finals = [f for f in outdir.glob("*.mp4")]
    checks.append(("final/ 只有一个成片", len(finals) == 1,
                   f"{len(finals)} 个 mp4" + ("：" + "、".join(f.name for f in finals) if len(finals) > 1 else "")))
    bad = [c for c in checks if not c[1]]
    lines = ["# 08 交付", "", f"- 成片：`{final}`", f"- 字幕：`{ass}`（{len(cues)} 条，{st['font']} {st['size']}px，MarginV {st['margin_v']}）",
             f"- 时长：{fv['duration']:.2f}s（音轨 {fa['duration']:.2f}s）", "", "## QC", "", "| 项 | 结果 | 实测 |", "|---|---|---|"]
    for name, ok, val in checks:
        lines.append(f"| {name} | {'✓' if ok else '✗'} | {val} |")
    (ws / "08-final-delivery.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, ok, val in checks:
        print(f"{'✓' if ok else '✗'} {name}（{val}）")
    print(f"{'✓' if not bad else '✗'} 成片 → {final}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
