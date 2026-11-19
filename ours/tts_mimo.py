#!/usr/bin/env python3
"""04 配音：02-final-script.md → audio/main-voice.wav（MiMo 分块并发 → 顺序拼接）。

这是对 `mimo-tts-generator` 的薄封装：只做「语义分块 + 并发调用 + 顺序拼接 + 时长入档」，
不改文案、不改 CTA（文案问题回 02）。没有 MIMO_API_KEY 时直接报错，不静默降级成机器音。

用法：
  python3 ours/tts_mimo.py --script 02-final-script.md --account accounts/family-education-parent-reader.md \
      --out audio/main-voice.wav
  python3 ours/tts_mimo.py --script 02-final-script.md --voice 白桦 --style-file metadata/style.txt
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIMO = Path("/root/.pi/agent/skills/mimo-tts-generator/scripts/generate_mimo_tts.py")
DEFAULT_STYLE = {
    "茉莉": "角色：普通妈妈型读书分享者，读家庭教育书有真实触动的人。场景：在家对着手机跟另一位妈妈说话。"
            "指导：真诚、温和、有分享欲；语速中速；第一句清楚有气口。禁用：播音腔、老师腔、卖课腔、喊麦、哭腔。",
    "白桦": "角色：传统文化书普通读书分享者，不是国学大师。场景：安静书房里把古人经验讲给朋友听。"
            "指导：沉稳、克制、有温度；语速中等偏慢；讲到转折时略提气。禁用：朗诵腔、说教腔、卖课腔。",
}


def die(msg: str) -> "SystemExit":
    raise SystemExit(f"✗ {msg}")


def flush(text: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", text], capture_output=True, text=True)
    return float(out.stdout.strip() or 0) if out.returncode == 0 else 0.0


def read_body(path: Path) -> str:
    lines = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith(("#", ">", "|", "---")):
            continue
        if re.match(r"^[\w\u4e00-\u9fff-]+:\s", s) and len(s.split(":")[0]) <= 12:
            continue
        lines.append(s)
    if not lines:
        die(f"{path} 里没有正文")
    return "\n".join(lines)


def chunks(body: str, lo: int = 180, hi: int = 350) -> list[str]:
    """按段落/句子攒到 180–350 字一段：MiMo 上下文 8K，但太长的段落语气会塌，按语义节拍切最好。"""
    sents = [s for s in re.split(r"(?<=[。！？!?；;])", body.replace("\n", "")) if s.strip()]
    out, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > hi:
            out.append(cur); cur = s
        else:
            cur += s
        if len(cur) >= lo and (cur.endswith(("。", "！", "？", "；")) or len(cur) >= hi):
            out.append(cur); cur = ""
    if cur.strip():
        out.append(cur)
    return out or [body]


def voice_of(account: Path | None) -> tuple[str, str]:
    voice, program = "茉莉", "booklist-htmlmotion-default"
    if account and account.exists():
        txt = account.read_text(encoding="utf-8")
        m = re.search(r"音色：`?([^`\n（]+)", txt)
        if m:
            voice = m.group(1).strip()
        m = re.search(r"program_name：`?([^`\n ]+)", txt)
        if m:
            program = m.group(1).strip()
    return voice, program


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="02-final-script.md")
    ap.add_argument("--account", help="账号 md：取音色与 program_name")
    ap.add_argument("--voice", help="直接指定音色（覆盖账号）")
    ap.add_argument("--style-file", help="自然语言声音导演（user content）；不写用内置默认")
    ap.add_argument("--out", default="audio/main-voice.wav")
    ap.add_argument("--work", default="metadata/04-voice")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--mimo-script", default=str(MIMO))
    a = ap.parse_args()

    if not Path(a.mimo_script).exists():
        die(f"找不到 mimo-tts-generator：{a.mimo_script}（--mimo-script 指定路径）")
    if not (Path("/root/.pi/agent/skills/mimo-tts-generator/.env.local").exists()
            or __import__("os").environ.get("MIMO_API_KEY")):
        die("没有 MIMO_API_KEY：在 mimo-tts-generator/.env.local 里配，或 export MIMO_API_KEY（不做静默降级）")

    body = read_body(Path(a.script))
    voice, program = voice_of(Path(a.account) if a.account else None)
    if a.voice:
        voice = a.voice
    style = Path(a.style_file).read_text(encoding="utf-8").strip() if a.style_file else DEFAULT_STYLE.get(voice, DEFAULT_STYLE["茉莉"])
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    parts = chunks(body)
    print(f"04 配音：{len(body)} 字 → {len(parts)} 段（{voice} / {program}）")

    def one(i: int, text: str) -> dict:
        sid = f"{i + 1:03d}"
        (work / f"{sid}-user.txt").write_text(style, encoding="utf-8")
        (work / f"{sid}-assistant.txt").write_text(text, encoding="utf-8")
        wav = work / f"{sid}.wav"
        meta = work / f"{sid}.json"
        cmd = [sys.executable, a.mimo_script,
               "--style-file", str(work / f"{sid}-user.txt"),
               "--text-file", str(work / f"{sid}-assistant.txt"),
               "--voice", voice, "--audio-format", "wav",
               "--segment-id", sid, "--program-name", program,
               "--download-to", str(wav), "--output", str(meta)]
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not wav.exists():
            raise RuntimeError(f"段 {sid} 失败：{((r.stderr or r.stdout or '').strip()[-400:])}")
        return {"id": sid, "chars": len(text), "wav": str(wav), "seconds": round(time.time() - t0, 1),
                "duration": flush(wav), "text": text}

    recs = []
    with ThreadPoolExecutor(max_workers=max(1, a.parallel)) as ex:
        for rec in ex.map(lambda iv: one(*iv), list(enumerate(parts))):
            recs.append(rec)
            print(f"  ✓ {rec['id']} {rec['chars']} 字 {rec['duration']:.2f}s（{rec['seconds']}s 生成）")
    recs.sort(key=lambda r: r["id"])

    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{Path(r['wav']).resolve()}'\n" for r in recs), encoding="utf-8")
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:a", "pcm_s16le", str(out)], check=True)
    total = flush(out)
    if total < 10:
        die(f"拼接后只有 {total:.1f}s，疑似漏段")
    (work / "04-audio.json").write_text(json.dumps(
        {"voice": voice, "program_name": program, "chars": len(body), "segments": recs,
         "duration_seconds": round(total, 2), "output": str(out), "style": style}, ensure_ascii=False, indent=1), encoding="utf-8")
    Path("04-audio.md").write_text(
        f"# 04 主音轨\\n\\n- 音色：{voice}（{program}）\\n- 文案：{len(body)} 字 / {len(recs)} 段\\n"
        f"- 成轨：`{out}` · **{total:.2f}s**\\n- 生成耗时：{sum(r['seconds'] for r in recs):.0f}s（并发 {a.parallel}）\\n",
        encoding="utf-8")
    print(f"✓ {out} · {total:.2f}s · {len(recs)} 段")
    return 0


if __name__ == "__main__":
    sys.exit(main())
