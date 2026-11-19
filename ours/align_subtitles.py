#!/usr/bin/env python3
"""08a 字幕对齐：让每条字幕贴着语音说出来的那一刻（不靠猜，不靠固定镜长）。

方法：ffmpeg `silencedetect` 找停顿 → 得到「说话段」→ 把 02 的句子按字数分配到说话段上。
不依赖任何 API key，也不依赖 ASR 模型；换音轨/改文案后重跑即可。
（以后有 GROQ key 想上 ASR：`--captions` 直接喂 assemble 即可，本脚本作为无 key 时的默认路径。）

用法：
  python3 ours/align_subtitles.py --audio audio/main-voice.wav --script 02-final-script.md \
      --out metadata/captions.json
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys
from pathlib import Path

PAUSE_DB = -32          # 停顿判定（dB）
MIN_SIL = 0.26          # 这么长的静音才算一句之间的停顿
MIN_CAP, MAX_CAP = 0.7, 14.0


def die(msg: str) -> "SystemExit":
    raise SystemExit(f"✗ {msg}")


def probe(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        die(f"ffprobe 打不开 {path}")
    return float(r.stdout.strip())


def silences(audio: Path) -> list[tuple[float, float]]:
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(audio), "-af",
                        f"silencedetect=noise={PAUSE_DB}dB:d={MIN_SIL}", "-f", "null", "-"],
                       capture_output=True, text=True)
    txt = r.stderr
    starts = [float(m) for m in re.findall(r"silence_start:\s*([0-9.]+)", txt)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([0-9.]+)", txt)]
    return list(zip(starts, ends))


def speech_spans(audio: Path) -> tuple[list[tuple[float, float]], float]:
    total = probe(audio)
    sil = silences(audio)
    spans, cur = [], 0.0
    for s, e in sil:
        if s - cur > 0.20:
            spans.append((cur, s))
        cur = max(cur, e)
    if total - cur > 0.20:
        spans.append((cur, total))
    if not spans:
        spans = [(0.0, total)]
    return spans, total


def sentences(script: Path) -> list[str]:
    body = []
    for ln in script.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith(("#", ">", "|", "---")):
            continue
        if re.match(r"^[\w\u4e00-\u9fff-]+:\s", s) and len(s.split(":")[0]) <= 12:
            continue
        body.append(s)
    text = "".join(body)
    # 一条字幕 = 一个完整句子（不在这里硬切成 14 字：切了会断词、也会让时间对不齐）。
    # 折行交给 assemble.py 的 wrap_sub（每行 ≤12 汉字、最多 3 行）。
    return [p.strip() for p in re.split(r"(?<=[。！？!?；;])", text) if p.strip()]


def fit_spans(spans: list[tuple[float, float]], caps: list[str]) -> list[tuple[float, float, str]]:
    """说话段数 ≠ 字幕条数时：段多就按最短空隙合并，段少就按字数切最长的段。"""
    spans = list(spans)
    while len(spans) > len(caps):
        gaps = [(spans[i + 1][0] - spans[i][1], i) for i in range(len(spans) - 1)]
        _, i = min(gaps)
        spans[i:i + 2] = [(spans[i][0], spans[i + 1][1])]
    while len(spans) < len(caps):
        need = len(caps) - len(spans)
        weights = [0.0] * len(spans)
        idx = 0
        for c in caps:                                   # 先按字数把字幕分配到段上，再切最挤的那段
            weights[idx % len(spans)] += len(c)
            idx += 1
        order = sorted(range(len(spans)), key=lambda i: -(spans[i][1] - spans[i][0]) / max(1.0, weights[i]))
        out = []
        for i in order[:need]:
            s, e = spans[i]
            mid = s + (e - s) * 0.54
            spans[i:i + 1] = [(s, mid), (mid, e)]
        if len(spans) >= len(caps):
            break
    return [(s, e, c) for (s, e), c in zip(spans, caps)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default="audio/main-voice.wav")
    ap.add_argument("--script", default="02-final-script.md")
    ap.add_argument("--out", default="metadata/captions.json")
    ap.add_argument("--report", default="metadata/subtitle-align.json")
    a = ap.parse_args()
    audio, script = Path(a.audio), Path(a.script)
    for p in (audio, script):
        if not p.exists():
            die(f"缺文件：{p}")

    caps = sentences(script)
    if not caps:
        die(f"{script} 里没有正文")
    spans, total = speech_spans(audio)
    rows = fit_spans(spans, caps)

    out, prev_end = [], 0.0
    for i, (s, e, text) in enumerate(rows):
        s = max(s, prev_end + 0.02)
        e = max(e, s + MIN_CAP)
        if i == len(rows) - 1:
            e = min(max(e, s + MIN_CAP), total - 0.05)
        e = min(e, s + MAX_CAP)
        if e <= s:
            e = s + MIN_CAP
        out.append({"start": round(s, 3), "end": round(e, 3), "text": text})
        prev_end = e
    # 完整性：每条字幕时长合理、不重叠、覆盖到结尾
    bad = [o for o in out if not (MIN_CAP - 1e-6 <= o["end"] - o["start"] <= MAX_CAP + 1e-6)]
    if bad:
        die(f"{len(bad)} 条字幕时长越界：{bad[0]}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    covered = out[-1]["end"] - out[0]["start"]
    rep = {"method": "silencedetect", "pause_db": PAUSE_DB, "min_silence": MIN_SIL,
           "audio_seconds": round(total, 2), "speech_spans": len(spans), "captions": len(out),
           "covered_seconds": round(covered, 2), "chars": sum(len(o["text"]) for o in out),
           "chars_per_second": round(sum(len(o["text"]) for o in out) / max(1e-6, covered), 2)}
    Path(a.report).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ 字幕 {len(out)} 条 / 语音 {total:.2f}s · {rep['chars_per_second']} 字每秒 · 说话段 {len(spans)} → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
