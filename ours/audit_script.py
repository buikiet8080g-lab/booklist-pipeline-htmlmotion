#!/usr/bin/env python3
"""03 文案审核（内容层，不是事实层）：改写后的稿子能不能直接开口念。

审六件事（都对「口播稿」这个用途）：
  1. 覆盖率   —— 原稿的信息有没有被覆盖（句子级），别把两篇稿只用了一篇
  2. 句长     —— 一句念不完就是事故（>28 字黄，>32 字红）
  3. 口语化   —— 书面连接词/黑话/术语（综上所述、赋能、抓手、闭环、维度…）
  4. 对话感   —— 有没有对着观众说（第二人称「你」/问句）
  5. 事实保留 —— 原稿里的数字/年份/倍数有没有被悄悄删掉
  6. 硬伤     —— 书名号不配对、句末没标点、连续重复词、绝对化广告语

用法：
  python3 ours/audit_script.py --script 02-final-script.md --sources sources/a.txt sources/b.txt \
      --book "被讨厌的勇气" --out 03-script-audit.md
  python3 ours/audit_script.py --script 02-final-script.md            # 没原稿时只审文字质量
退出码：0 绿/黄（可继续）｜1 红（回 02 改稿）
"""
from __future__ import annotations

import argparse, json, re, sys
from pathlib import Path

# 书面词 / 黑话 / 术语：念出来不像人话
WRITTEN = ["综上所述", "基于此", "综上所述", "由此可见", "因此我们", "旨在", "以便", "从而", "进而",
           "赋能", "抓手", "闭环", "链路", "底层逻辑", "颗粒度", "范式", "维度", "生态位", "方法论",
           "认知升级", "复利效应", "心流", "内耗", "熵增", "第一性原理", "长期主义", "护城河"]
HEDGE = ["在一定程度上", "从某种意义上说", "毋庸置疑", "众所周知"]
ABSOLUTE = ["最好的", "唯一", "彻底改变", "包治", "永久有效", "百分之百", "第一名", "第一品牌", "第一选择"]
CTA = re.compile(r"(橱窗|左下角|评论区|链接|购买|下单|点开|带走|关注)")


def die(msg: str) -> "SystemExit":
    raise SystemExit(f"✗ {msg}")


def norm(s: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9%]", "", s)


def bigrams(s: str) -> set[str]:
    s = norm(s)
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s[:1]}


def jac(a: str, b: str) -> float:
    A, B = bigrams(a), bigrams(b)
    return len(A & B) / max(1, len(A | B))


def sentences(text: str) -> list[str]:
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith(("#", ">", "|", "---")):
            continue
        if re.match(r"^[\w\u4e00-\u9fff-]+:\s", ln) and len(ln.split(":")[0]) <= 12:
            continue
        out += [p.strip() for p in re.split(r"(?<=[。！？!?；;])", ln) if p.strip()]
    return out


def read_sources(paths: list[str], src_dir: str | None) -> list[tuple[str, list[str]]]:
    ps = [Path(p) for p in paths]
    if src_dir:
        ps += sorted(p for p in Path(src_dir).iterdir() if p.suffix.lower() in (".txt", ".md"))
    out = []
    for p in ps:
        if p.exists():
            out.append((p.name, sentences(p.read_text(encoding="utf-8"))))
    return out


def covered(src: str, new_sents: list[str]) -> tuple[bool, str]:
    """源句被覆盖：任一新句与它 bigram Jaccard ≥0.35，或源句里 ≥8 字的连续片段原样出现在新稿。"""
    n = norm(src)
    for s in new_sents:
        if jac(src, s) >= 0.35:
            return True, s
    for i in range(0, max(0, len(n) - 8) + 1):
        frag = n[i:i + 8]
        if frag and any(frag in norm(x) for x in new_sents):
            return True, frag
    return False, ""


def audit(lines: list[str], sources: list[tuple[str, list[str]]], book: str) -> dict:
    red, yellow, info = [], [], {}
    text = "".join(lines)
    chars = len(norm(text))
    if chars < 60:
        red.append(f"正文只有 {chars} 字，撑不起一条片（<60 字；120 字以上才够 30s+）")
    elif chars < 120:
        yellow.append(f"正文 {chars} 字偏短（只够 ~{chars/4.2:.0f}s；30s 以上建议 ≥120 字）")

    # 1 覆盖率（有原稿才算）
    cov = []
    if sources:
        for name, sents in sources:
            if not sents:
                continue
            hit = [s for s in sents if covered(s, lines)[0]]
            cov.append({"source": name, "sentences": len(sents), "covered": len(hit),
                        "ratio": round(len(hit) / len(sents), 2),
                        "missing": [s for s in sents if not covered(s, lines)[0]][:8]})
        total_r = sum(c["ratio"] for c in cov) / len(cov)
        info["coverage"] = total_r
        if total_r < 0.55:
            red.append(f"覆盖率 {total_r:.0%} < 55%：新稿丢了原稿一半以上的信息，回 02 补")
        elif total_r < 0.70:
            yellow.append(f"覆盖率 {total_r:.0%} 偏低（目标 ≥70%）")
        for c in cov:
            if c["ratio"] < 0.40:
                red.append(f"《{c['source']}》只覆盖了 {c['ratio']:.0%}：两篇稿不会只用了一篇吧？")

    # 2 句长
    lens = [len(norm(x)) for x in lines]
    info["max_sentence"] = max(lens) if lens else 0
    info["avg_sentence"] = round(sum(lens) / max(1, len(lens)), 1)
    for x in lines:
        n = len(norm(x))
        if n > 32:
            red.append(f"句子 {n} 字念不完（≤28 最稳）：{x[:24]}…")
        elif n > 28:
            yellow.append(f"句子 {n} 字偏长：{x[:24]}…")

    # 3 口语化 / 书面词
    hits = [w for w in WRITTEN + HEDGE if w in text]
    info["written_words"] = hits
    if len(hits) >= 3:
        red.append(f"书面词/黑话 {len(hits)} 个：{'、'.join(hits[:6])}（念出来不像人话，换成大白话）")
    elif hits:
        yellow.append(f"书面词/黑话：{'、'.join(hits)}（建议换掉）")

    # 4 对话感
    you = len(re.findall(r"[你您]", text))
    q = text.count("？") + text.count("?")
    info["you_per_100"] = round(you / max(1, chars) * 100, 1)
    info["questions"] = q
    if you / max(1, chars) * 100 < 2 and q == 0:
        msg = "通篇没有「你」也没有问句：不是对着观众说话，改成对话口吻"
        (yellow if chars < 150 else red).append(msg)          # 很短的稿子先给黄灯，正片才红

    # 5 事实保留：原稿数字有没有被删
    src_nums = set()
    for _, sents in sources:
        for s in sents:
            src_nums |= set(re.findall(r"\d+(?:\.\d+)?%?", s))
    missing = sorted(n for n in src_nums if n not in text)
    info["numbers_missing"] = missing
    if len(missing) >= 3:
        red.append(f"原稿里的 {len(missing)} 个数字没进新稿：{'、'.join(missing[:8])}（删事实要写进 02-rewrite-record.md）")
    elif missing:
        yellow.append(f"原稿数字被删：{'、'.join(missing)}（确认是有意删）")

    # 6 硬伤
    if text.count("《") != text.count("》"):
        red.append("书名号不配对")
    if book and f"《{book}》" not in text and book not in text:
        yellow.append(f"全篇没提到书名《{book}》")
    for w in ABSOLUTE:
        if w in text:
            yellow.append(f"绝对化表述「{w}」：广告合规风险")
    for x in lines:
        if not re.search(r"[。！？!?；;]$", x):
            red.append(f"句子没有句末标点（TTS 会连读）：{x[:20]}…")
    for x in lines:
        if re.search(r"(.)\1{2,}", x):
            yellow.append(f"连续重复字：{x[:20]}…")
    if not CTA.search("".join(lines[-2:])):
        red.append("最后两句没有 CTA（橱窗/左下角/点开）")

    info["chars"] = chars
    info["sentences"] = len(lines)
    verdict = "red" if red else ("yellow" if yellow else "green")
    return {"verdict": verdict, "red": red, "yellow": yellow, "info": info, "coverage": cov}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="02-final-script.md")
    ap.add_argument("--sources", nargs="*", default=[])
    ap.add_argument("--source-dir")
    ap.add_argument("--book", default="")
    ap.add_argument("--out", default="03-script-audit.md")
    ap.add_argument("--json", default="metadata/03-script-audit.json")
    ap.add_argument("--min-coverage", type=float, default=0.55)
    a = ap.parse_args()
    script = Path(a.script)
    if not script.exists():
        die(f"没有 {script}")
    lines = sentences(script.read_text(encoding="utf-8"))
    sources = read_sources(a.sources, a.source_dir)
    rep = audit(lines, sources, a.book)
    rep["info"]["sources"] = [c["source"] for c in rep["coverage"]]
    rep["info"]["min_coverage"] = a.min_coverage

    md = ["# 03 文案审核（内容层）", "",
          f"- 稿子：`{script}` · {rep['info']['sentences']} 句 / {rep['info']['chars']} 字 · 最长句 {rep['info']['max_sentence']} 字 · 平均 {rep['info']['avg_sentence']} 字",
          f"- 原稿：{', '.join(rep['info']['sources']) or '（无，只审文字质量）'}",
          f"- 结论：**{'红（回 02 改）' if rep['verdict']=='red' else ('黄（可发，建议改）' if rep['verdict']=='yellow' else '绿（可用）')}**", ""]
    if rep["coverage"]:
        md += ["## 覆盖率（原稿信息有没有丢）", "", "| 原稿 | 句数 | 覆盖 | 覆盖率 |", "|---|---|---|---|"]
        md += [f"| {c['source']} | {c['sentences']} | {c['covered']} | {c['ratio']:.0%} |" for c in rep["coverage"]]
        md += [""]
        for c in rep["coverage"]:
            if c["missing"]:
                md += [f"- **{c['source']} 未覆盖**：" + "；".join(x[:30] for x in c["missing"])]
        md += [""]
    md += ["## 口播质量", "", "| 项 | 实测 | 判据 |", "|---|---|---|",
           f"| 最长句 | {rep['info']['max_sentence']} 字 | ≤28 稳，>32 红 |",
           f"| 平均句长 | {rep['info']['avg_sentence']} 字 | 12–22 |",
           f"| 对话感（你/百字） | {rep['info']['you_per_100']} | ≥2 |",
           f"| 问句 | {rep['info']['questions']} | ≥1 更好 |",
           f"| 书面词/黑话 | {'、'.join(rep['info']['written_words']) or '无'} | 0–2 |",
           f"| 原稿数字未进新稿 | {'、'.join(rep['info']['numbers_missing']) or '无'} | 0–2 |", ""]
    md += ["## 红灯", ""] + ([f"- ✗ {x}" for x in rep["red"]] or ["- 无"]) + [""]
    md += ["## 黄灯", ""] + ([f"- ! {x}" for x in rep["yellow"]] or ["- 无"]) + [""]
    md += ["## 改了什么（自动记录）", "",
           "改写时保留/合并/删除的明细在 `02-rewrite-record.md`；本文件只判「该保的有没有保住、念出来顺不顺」。" , ""]
    Path(a.out).write_text("\n".join(md), encoding="utf-8")
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")

    for x in rep["red"]:
        print(f"✗ {x}")
    for x in rep["yellow"]:
        print(f"! {x}")
    print(f"{'✗' if rep['verdict']=='red' else '✓'} 03 审核：{rep['info']['sentences']} 句 / {rep['info']['chars']} 字 · "
          f"覆盖 {rep['info'].get('coverage', 0):.0%} · {len(rep['red'])} 红 / {len(rep['yellow'])} 黄 → {a.out}")
    return 1 if rep["verdict"] == "red" else 0


if __name__ == "__main__":
    sys.exit(main())
