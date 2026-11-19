#!/usr/bin/env python3
"""02 整合改写：一篇或多篇同书文案 → 一条可直接配音的口播稿（机械版 + 给模型用的改写清单）。

两种用法：
  A. 机械整合（无模型也能跑通，可复现）：
     python3 ours/rewrite_script.py --book "被讨厌的勇气" --sources a.txt b.txt --out 02-final-script.md
  B. 给主 Agent 做改写（质量更好）：同一份输入，先 `--brief` 打印「保留/合并/删掉」的清单与约束，
     模型照 constraints 自己写 02-final-script.md，再跑 `--check` 校验结构。

它做什么（A 路径）：
  · 清平台噪音（关注/点赞/转发/公众号/橱窗/链接/emoji/#话题/“以下是正文”这类）
  · 分句 → 去重（归一化后 12 字前缀相同或字符 bigram 相似度 ≥0.82 视为重复）
  · 打分保留（书内观点 > 数字/年份 > 方法步骤 > 故事；纯情绪句降权）
  · 按原顺序拼成一篇，字数对齐目标（默认 4.2 字/秒 × 目标时长）
  · 结尾补一句 CTA（没有现成的、或原 CTA 被删时）
  · 输出 02-final-script.md + 02-rewrite-record.md

它不做什么：不编事实、不新增数字。原稿没有的数与页码，一律不写。
"""
from __future__ import annotations

import argparse, json, re, sys
from pathlib import Path

# 平台噪音：命中就整句丢弃（CTA 由结尾统一生成，不需要原稿里的 CTA 句）
NOISE = re.compile(r"(关注|点赞|转发|收藏|评论区|私信|公众号|视频号|橱窗|点击.{0,6}(链接|购买|下单)|"
                   r"以下[是为]正文|未完待续|#\S+|抖音|快手|小红书|B站|下期|接着讲|敬请期待|记得关注|主页|置顶)")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
CTA_HINT = re.compile(r"(橱窗|左下角|评论区|链接|购买|下单|点开|带走)")


def die(msg: str) -> "SystemExit":
    raise SystemExit(f"✗ {msg}")


def clean(text: str) -> str:
    text = EMOJI.sub("", text)
    text = re.sub(r"【[^】]{0,12}】", "", text)          # 栏目标记
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；;])|\n", text)
    out = []
    for p in parts:
        p = p.strip(" \u3000")
        if not p:
            continue
        if len(p) < 6:                       # 太短的碎句并到上一句
            if out:
                out[-1] += p
            continue
        out.append(p)
    return out


def norm(s: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s)


def bigrams(s: str) -> set[str]:
    s = norm(s)
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def dup(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    if na[:12] == nb[:12]:
        return True
    A, B = bigrams(a), bigrams(b)
    return len(A & B) / max(1, len(A | B)) >= 0.82


def score(s: str, book: str) -> float:
    v = 1.0
    if book and book in s:
        v += 0.8
    if re.search(r"\d", s):
        v += 0.5
    if re.search(r"[“「『]", s):
        v += 0.7
    if re.search(r"(第一|第二|第三|一是|二是|三是|先|再|最后)", s):
        v += 0.4
    if re.search(r"(其实|真正|关键|本质|原因|因为|所以)", s):
        v += 0.3
    if re.search(r"(难过|崩溃|心疼|哭了|开心)", s):
        v -= 0.3
    if CTA_HINT.search(s):
        v -= 0.6                            # CTA 不占正文额度，结尾单独补
    if len(s) > 46:
        v -= 0.2
    return v


def cta_for(book: str, account: str) -> str:
    if account and "traditional" in account:
        return f"想读《{book}》的，橱窗里有，点开就能带走。"
    return f"这本书我放在橱窗了，想读《{book}》的点开看看。"


def build(sources: list[str], book: str, target_chars: int, account: str) -> tuple[list[str], list[dict]]:
    kept, dropped, seen = [], [], []
    for si, src in enumerate(sources):
        for s in split_sentences(clean(src)):
            if NOISE.search(s):
                dropped.append({"text": s, "why": "平台噪音/CTA", "source": si + 1})
                continue
            if any(dup(s, k) for k in seen):
                dropped.append({"text": s, "why": "重复", "source": si + 1})
                continue
            seen.append(s)
            kept.append({"text": s, "score": score(s, book), "source": si + 1, "idx": len(kept)})
    # 预算：先留 CTA 的位置（约 20 字）
    budget = max(120, target_chars - 22)
    chosen, total = [], 0
    # 第一句是钩子：一定要留（多为痛点/场景），不管分数
    if kept:
        chosen.append(kept[0]); total += len(kept[0]["text"])
    rest = [k for k in kept[1:] if not CTA_HINT.search(k["text"])]
    rest.sort(key=lambda k: (-k["score"], k["idx"]))
    for k in rest:
        if total + len(k["text"]) > budget:
            dropped.append({"text": k["text"], "why": "超字数", "source": k["source"]})
            continue
        chosen.append(k); total += len(k["text"])
    chosen.sort(key=lambda k: k["idx"])                       # 回到原顺序讲
    lines = [k["text"] if k["text"].endswith(("。", "！", "？", "；")) else k["text"] + "。" for k in chosen]
    lines.append(cta_for(book, account))
    return lines, dropped


def check(lines: list[str], book: str) -> list[str]:
    problems = []
    if not lines:
        problems.append("没有正文")
    if not any(CTA_HINT.search(x) for x in lines[-2:]):
        problems.append("最后两句里没有 CTA（橱窗/左下角/点开）")
    for i, x in enumerate(lines):
        if len(x) > 60:
            problems.append(f"第 {i+1} 句 {len(x)} 字过长（口播一句建议 ≤28 字，最多 60）")
        if x.count("《") != x.count("》"):
            problems.append(f"第 {i+1} 句书名号不配对")
    if book and not any(book in x for x in lines):
        problems.append(f"全篇没提到书名《{book}》")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--sources", nargs="*", help="一篇或多篇原始文案（txt/md 都行）")
    ap.add_argument("--source-dir", help="或给一个目录，里面每个 .txt/.md 都算一篇")
    ap.add_argument("--out", default="02-final-script.md")
    ap.add_argument("--record", default="02-rewrite-record.md")
    ap.add_argument("--target-seconds", type=float, default=120, help="目标成片秒数（决定字数）")
    ap.add_argument("--chars-per-second", type=float, default=4.2)
    ap.add_argument("--account", default="")
    ap.add_argument("--brief", action="store_true", help="只打印给模型看的改写清单与约束")
    ap.add_argument("--check", action="store_true", help="只校验已有的 --out")
    a = ap.parse_args()

    if a.check:
        lines = [x for x in Path(a.out).read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]
        probs = check(lines, a.book)
        for p in probs:
            print(f"✗ {p}")
        print(f"{'✓' if not probs else '✗'} 结构校验：{len(lines)} 句 / {sum(len(x) for x in lines)} 字")
        return 1 if probs else 0

    paths = [Path(p) for p in (a.sources or [])]
    if a.source_dir:
        paths += sorted(p for p in Path(a.source_dir).iterdir() if p.suffix.lower() in (".txt", ".md"))
    if not paths:
        die("给 --sources a.txt b.txt 或 --source-dir 目录")
    sources = []
    for p in paths:
        if not p.exists():
            die(f"找不到 {p}")
        sources.append(p.read_text(encoding="utf-8"))
    target = int(a.target_seconds * a.chars_per_second)
    lines, dropped = build(sources, a.book, target, a.account)

    if a.brief:
        print(json.dumps({"book": a.book, "target_chars": target, "sources": [str(p) for p in paths],
                          "kept": lines, "dropped": dropped[:40],
                          "constraints": ["一句 12–28 字，口语，不写书面连接词",
                                          "保留原稿里的数字/引文/书名，不自造事实与页码",
                                          f"结尾必须有一句 CTA（提到《{a.book}》+ 橱窗/左下角）",
                                          f"总字数 {int(target*0.85)}–{int(target*1.15)}"]},
                         ensure_ascii=False, indent=1))
        return 0

    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    rec = [f"# 02 整合改写记录", "",
           f"- 书：`{a.book}`｜原稿 {len(paths)} 篇：{', '.join(p.name for p in paths)}",
           f"- 目标：{a.target_seconds:.0f}s × {a.chars_per_second} 字/秒 ≈ {target} 字；实际 {sum(len(x) for x in lines)} 字 / {len(lines)} 句",
           "", "## 保留（按原顺序）", ""]
    rec += [f"{i+1}. {x}" for i, x in enumerate(lines)]
    rec += ["", "## 删掉", ""]
    rec += [f"- [{d['why']}] 来自第 {d['source']} 篇：{d['text'][:40]}" for d in dropped[:60]] or ["- （无）"]
    Path(a.record).write_text("\n".join(rec) + "\n", encoding="utf-8")
    probs = check(lines, a.book)
    print(f"✓ {out} · {len(lines)} 句 · {sum(len(x) for x in lines)} 字（目标 {target}）")
    print(f"✓ {a.record} · 删掉 {len(dropped)} 句")
    for p in probs:
        print(f"! {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
