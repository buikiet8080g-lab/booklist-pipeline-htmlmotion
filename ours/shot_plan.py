#!/usr/bin/env python3
"""05 分镜计划：02-final-script.md（+ 主音轨时长 + 01 书封资产）→ metadata/plan.json + 05-shot-plan.md。

主路径是「自动切镜」：按句子权重把音轨时长分给每一镜，每镜 6–8s（引文 8–12s、数据链最多 15s），
再按 §15.4 的白名单挑语法（只出 bl_cover_hero / bl_quote / y5 / t3 / y2 五种）。
模型要覆盖某一镜的文案或版式时，给一份 --sheet（JSON 数组，按顺序对齐镜头），不写就用自动结果。

用法：
  python3 ours/shot_plan.py --script 02-final-script.md --audio audio/main-voice.wav \
      --book metadata/book-assets.json --theme wood --out metadata/plan.json --markdown 05-shot-plan.md
  # 覆盖：--sheet metadata/sheet.json
"""
from __future__ import annotations

import argparse, json, re, subprocess
from pathlib import Path

CANVAS = {"width": 720, "height": 1280, "fps": 24}
SAFE = {"top": 80, "bottom": 300, "left": 48, "right": 48}
WHITELIST = ["bl_cover_hero", "bl_quote", "y5_kinetic_type", "t3_finance_chart", "y2_vox"]
PIPELINE = {
    "pipeline": "booklist-pipeline-htmlmotion", "pipeline_version": 1.2,
    "render_engine": "huashu_grammar_vendor", "canvas": "720x1280@24",
    "shot_duration_default": "6-8s", "shot_duration_long_max": "15s", "shot_cut": "hard_cut",
    "subtitle_safe_bottom_px": 300, "grammar_whitelist": WHITELIST,
    "free_scene_max_ratio": 0.10, "user_confirmation_points": 0,
}
MIN_D, MAX_D = 5.5, 8.0


def die(msg: str) -> "SystemExit":
    raise SystemExit(f"✗ {msg}")


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    if out.returncode != 0:
        die(f"ffprobe 读不到音频时长：{path}\n{out.stderr.strip()}")
    return float(out.stdout.strip())


def read_script(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith(">") or s.startswith("|") or s.startswith("---"):
            continue
        if re.match(r"^[\w\u4e00-\u9fff-]+:\s", s) and len(s.split(":")[0]) <= 12:   # 产物文件里的 `字段: 值` 头
            continue
        lines.append(s)
    if not lines:
        die(f"{path} 里没有正文（02-final-script.md 只放纯正文，记录另存）")
    return "\n".join(lines)


def sentences(body: str) -> list[str]:
    body = body.replace("\n", "")
    parts = re.split(r"(?<=[。！？!?；;])", body)
    out = [p.strip() for p in parts if p.strip()]
    # 太短的碎句并到上一句（TTS 断句和字幕都按句走）
    merged: list[str] = []
    for s in out:
        if merged and len(s) < 6:
            merged[-1] += s
        else:
            merged.append(s)
    return merged


def group_sentences(sents: list[str], n: int) -> list[str]:
    """句子数比「每镜至少 5.5s」允许的镜数多时，合并相邻句（优先合并不含引文的），
    宁可少几镜也不出 <5s 的碎镜（书单号的碎镜读不完，且 lint 会红灯）。"""
    groups = [[x] for x in sents]
    quote = lambda t: bool(is_quote(t))
    while len(groups) > max(1, n):
        best, bi = None, None
        for i in range(len(groups) - 1):
            a, b = groups[i], groups[i + 1]
            cost = len("".join(a + b))
            if quote("".join(a)) or quote("".join(b)):
                cost += 400                       # 引文镜尽量独立，别被并进别人的镜
            if i == 0:
                cost += 250                       # 首镜（书籍导入）独立
            if i + 1 == len(groups) - 1:
                cost += 350                       # 尾镜是 CTA，必须独立，不能把正文内容并进去
            if best is None or cost < best:
                best, bi = cost, i
        a, b = groups[bi], groups[bi + 1]
        groups[bi:bi + 2] = [a + b]
    return ["".join(g) for g in groups]


def split_weight(weights: list[float], total: float, lo: float, hi: float) -> list[float]:
    """按权重分时长，并夹在 [lo, hi]；夹完把余量再分给还没到上限的。总和不保证等于 total，调用方再核。"""
    w = [max(1.0, x) for x in weights]
    d = [total * x / sum(w) for x in w]
    for _ in range(50):
        fixed = [min(max(x, lo), hi) for x in d]
        if fixed == d:
            break
        d = fixed
        free = [i for i, x in enumerate(d) if lo + 1e-6 < x < hi - 1e-6]
        if not free:
            break
        rest = total - sum(d)
        if abs(rest) < 1e-6:
            break
        wf = sum(w[i] for i in free)
        for i in free:
            d[i] = min(max(d[i] + rest * w[i] / wf, lo), hi)
    return d


def onscreen_pick(sentence: str, limit: int = 12) -> tuple[str, str]:
    """屏上字 ≤limit 字（§14.2 放宽到 12）。先按标点找自然断点，再退化到硬切；副句放剩下的半句。"""
    # 口播里最常见的是「书名：结论」结构：屏上字要的是冒号后面的那句结论，不是书名
    if "：" in sentence:
        sentence = sentence.rsplit("：", 1)[1]
    core = re.sub(r"[。！？!?；;，,、：:“”「」『』（）()]", " ", sentence).strip()
    chunks = [c for c in re.split(r"\s+", core) if c]
    if not chunks:
        return sentence[:limit], ""
    head = chunks[0]
    if len(head) > limit:
        head = head[:limit]
    rest = " ".join(chunks[1:])[:26]
    return head, rest


def split_points(sentence: str) -> list[str]:
    """「你能做的只有三件事：先看见情绪，再说明规则，最后给他选择」→ 3 个要点。
    y5 竖屏单页会空，能拆成 2–4 条就拆成清单（带进度轨），拆不出就单页。"""
    core = sentence.rsplit("：", 1)[1] if "：" in sentence else sentence
    parts = [p.strip(" 。！？；") for p in re.split(r"[，,、]", core)]
    parts = [p for p in parts if 2 <= len(p) <= 12]
    return parts if 2 <= len(parts) <= 4 else []


def is_quote(s: str) -> bool:
    """判「这一镜该用 bl_quote」：引号原文，或「书里说：……」这种把原文引出来的说法。"""
    if re.search(r"[“「『].{4,}[”」』]", s):
        return True
    m = re.search(r"(?:说|写道|原文|书里|书中)[：:]\s*(.{6,})", s)
    return bool(m and len(m.group(1)) <= 60)


def has_number(s: str) -> bool:
    return bool(re.search(r"\d", s)) and bool(re.search(r"[%倍岁元天次年个月]|成|小时", s))


def quote_payload(s: str, book: dict) -> dict:
    m = re.search(r"[“「『](.+?)[”」』]", s)
    if m:
        q = m.group(1).strip()
    else:
        # 「《书名》里说：把孩子的课题还给孩子。」→ 取冒号后到第一个句号前的那句原文
        m2 = re.search(r"(?:说|写道|原文|书里|书中)[：:]\s*([^。！？]{6,60})", s)
        q = m2.group(1).strip() if m2 else s.strip("。！？ ")
    q = q[:60]
    title = book.get("title", "")
    if title and not title.startswith(("《", "〈")):
        title = f"《{title}》"          # 出处行的书名要带书名号，否则读者看不出这是书
    return {"text": q, "data": {"source": title, "author": book.get("author", ""),
                                "page": book.get("quote_page", "")}}


def build_shot(idx: int, sentence: str, duration: float, start: float) -> dict:
    return {"id": f"{idx:03d}-1", "start": round(start, 3), "duration": round(duration, 3),
            "scene_type": "kit", "grammar": "y5_kinetic_type", "spec": {}, "narration_span": [round(start, 3), round(start + duration, 3)],
            "subtitle_lines": [sentence], "book_cover_required": False, "assets": [], "heavy_accent": False, "text": sentence}


def assign(shots: list[dict], book: dict, sheet: list[dict], plan_target: float) -> None:
    last = len(shots) - 1
    for i, sh in enumerate(shots):
        s = sh["text"]
        ov = sheet[i] if i < len(sheet) else {}
        g = ov.get("grammar")
        sh["_locked"] = bool(g)          # sheet 明确指定的语法不再被配比规则改掉（只在 lint 里报黄）
        if g and g not in WHITELIST:
            die(f"sheet 第 {i+1} 镜的 grammar「{g}」不在白名单 {WHITELIST}")
        if g:
            sh["grammar"] = g
        elif i == 0 or i == last:
            sh["grammar"] = "bl_cover_hero"
        elif is_quote(s):
            sh["grammar"] = "bl_quote"
        elif has_number(s) and ov.get("series"):
            sh["grammar"] = "t3_finance_chart"
        else:
            sh["grammar"] = "y5_kinetic_type"
        if sh["grammar"] == "bl_quote" and sh["duration"] < 7:
            sh["duration"] = 8.0

    # 配比兜底：文字主导 ≤30%（这里 y5 全算文字主导），每 3 镜至少 1 镜真实书封，不许连续 3 镜同语法
    cover_at = {0, last}
    for i in range(2, last, 3):
        cover_at.add(i)
    text_only = lambda sh: sh["grammar"] in ("y5_kinetic_type", "t3_finance_chart")
    for i in sorted(cover_at):
        if 0 < i < last and text_only(shots[i]) and not is_quote(shots[i]["text"]) and not shots[i].get("_locked"):
            shots[i]["grammar"] = "bl_cover_hero"
    # 连续三镜同语法 → 把中间那镜换成书封（书单号里最安全的换镜方式）
    for i in range(1, last):
        if (shots[i]["grammar"] == shots[i - 1]["grammar"] == shots[i + 1]["grammar"]
                and shots[i]["grammar"] != "bl_cover_hero" and not shots[i].get("_locked")):
            shots[i]["grammar"] = "bl_cover_hero"
    run = 0
    for sh in shots:
        run = run + 1 if sh["grammar"] == "y5_kinetic_type" else 0
        if run >= 3 and sh is not shots[-1] and not sh.get("_locked"):
            sh["grammar"] = "bl_cover_hero"
            run = 0
    # 书封镜不超过 40%（每片 3–5 次是上限，不是越多越好）
    cover_shots = [s for s in shots if s["grammar"] == "bl_cover_hero"]
    cap = max(1, int(len(shots) * 0.4))
    for sh in cover_shots[cap:]:
        if sh.get("_locked") or sh is shots[0] or sh is shots[-1]:
            continue          # 首镜（书籍导入）与尾镜（CTA）必须是书封，压低书封占比不能动这两端
        sh["grammar"] = "y5_kinetic_type"
    # 语法定了再对齐总时长：引文要 8s，别的镜就得让出来（原来先排时长再改语法，总长会超 2.5s）
    def bounds(sh):
        g = sh["grammar"]
        return (6.5, 12.0) if g == "bl_quote" else ((6.0, 15.0) if g == "t3_finance_chart" else (4.6, 8.0))
    target = float(plan_target)
    for _ in range(200):
        d = target - sum(s["duration"] for s in shots)
        if abs(d) < 0.05:
            break
        free = [s for s in shots if not (d < 0 and s["duration"] <= bounds(s)[0] + 1e-6) and not (d > 0 and s["duration"] >= bounds(s)[1] - 1e-6)]
        if not free:
            break
        step = d / len(free)
        for s in free:
            lo, hi = bounds(s)
            s["duration"] = round(min(max(s["duration"] + step, lo), hi), 3)
    t = 0.0
    for s in shots:
        s["start"] = round(t, 3)
        s["narration_span"] = [round(t, 3), round(t + s["duration"], 3)]
        t += s["duration"]


def make_spec(sh: dict, book: dict, theme: str) -> dict:
    g, s, ov = sh["grammar"], sh["text"], sh.get("_ov", {})
    head, rest = onscreen_pick(s)
    spec: dict = {}
    if g == "bl_cover_hero":
        spec = {"cues": [{"at": 0.06, "kind": "cover", "image": book["cover"],
                          "text": ov.get("text") or book.get("title", ""),
                          "sub": ov.get("sub") or book.get("author", ""),
                          "data": {"tag": ov.get("tag") or book.get("tag", ""), "press": book.get("publisher", "")}}]}
        sh["book_cover_required"] = True
        sh["assets"] = [{"role": "book_cover", "path": book["cover"]}]
    elif g == "bl_quote":
        q = quote_payload(s, book)
        spec = {"cues": [{"at": 0.06, "kind": "quote", "text": ov.get("text") or q["text"],
                          "data": {**q["data"], "key": ov.get("key", ""), "page": ov.get("page") or q["data"]["page"]}}]}
    elif g == "t3_finance_chart":
        series = ov.get("series") or []
        if not series:
            die(f"镜 {sh['id']} 选了 t3_finance_chart 但 sheet 没给 series（编数据是硬红线）")
        # t3 的 data.index 必须是柱子序号（数或数组），写 "all" 不会报错但一根都不长
        idx = list(range(len(series)))
        cues = [{"at": 0.4, "kind": "bar", "data": {"index": idx}}]
        if ov.get("highlight"):
            cues.append({"at": round(max(1.2, sh["duration"] * 0.62), 2), "kind": "highlight"})
        spec = {"data": {"title": ov.get("title") or head, "unit": ov.get("unit", ""), "source": ov.get("source", ""),
                         "chart": "bar", "decimals": ov.get("decimals", 0), "series": series,
                         "highlight": ov.get("highlight", {})},
                "cues": cues}
    elif g == "y2_vox":
        img = ov.get("image") or (sh["assets"][0]["path"] if sh["assets"] else None)
        if not img:
            die(f"镜 {sh['id']} 选了 y2_vox 但没有图片素材（y2 只承载真实素材，D18）")
        spec = {"cues": [{"at": 0.2, "kind": "image", "image": img, "text": ov.get("label", ""),
                          "data": {"tape": False}},
                         {"at": min(3.0, sh["duration"] * 0.5), "kind": "point", "text": ov.get("text") or head},
                         {"at": min(4.2, sh["duration"] * 0.75), "kind": "highlight", "data": ov.get("rect", {"rect": [0.15, 0.3, 0.7, 0.3]})}]}
    else:  # y5：一页一个要点。sheet 给 points（≥2 条）就出清单版式，y5 会画进度轨＋背景序号，竖屏不空
        auto_pts = split_points(s) if not ov.get("text") else []
        # 页数受时长约束：一页至少 1.7s，多出来的合并进最后一页（否则 cue 超出镜长会被 clip.js 丢掉，字就没了）
        max_pages = max(1, int((sh["duration"] - 0.4) / 1.7))
        if len(auto_pts) > max_pages:
            head_pts, tail = auto_pts[:max_pages - 1], "，".join(auto_pts[max_pages - 1:])
            auto_pts = head_pts + [tail]
        # 单页主词 ≤12 字（y5 竖屏两行内）：超过就在标点处再拆一页，**不许截断**（截断=丢字，lint D05 红）
        fixed = []
        for x in auto_pts:
            while len(x) > 12:
                cut = max((x.rfind(k, 0, 12) for k in "，。、；："), default=-1)
                cut = cut + 1 if cut >= 4 else 12
                fixed.append(x[:cut].strip("，。、；："))
                x = x[cut:].strip("，。、；：")
            if x:
                fixed.append(x)
        keep = max(1, int((sh["duration"] - 0.4) / 1.5))     # 一页约 1.5s；放不下的页不再截断，改挂到最后一页的辅句上
        pages = [{"text": x} for x in fixed[:keep]]
        extra = fixed[keep:]
        if extra and pages:
            pages[-1]["sub"] = "，".join(extra)[:40]
        pts = ov.get("points") or (pages if pages else [{"text": ov.get("text") or head, "sub": ov.get("sub") or rest}])
        step = max(1.8, (sh["duration"] - 0.6) / len(pts))
        cues = [{"at": round(0.06 + i * step, 2), "kind": "point", "text": p["text"], "sub": p.get("sub", "")}
                for i, p in enumerate(pts)]
        cues.append({"at": round(0.06 + max(0, len(pts) - 1) * step + min(1.6, step * 0.6), 2), "kind": "highlight",
                     "data": {"word": pts[-1]["text"][:4]}})
        spec = {"cues": cues}
    sh["spec"] = spec
    sh["theme"] = theme
    sh["safe"] = {"top": SAFE["top"], "bottom": SAFE["bottom"]}
    return sh


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--book", required=True, help="metadata/book-assets.json，或 auto（从文案里的《书名》推）")
    ap.add_argument("--cover", help="--book auto 时的书封路径（真实核验封面，必填）")
    ap.add_argument("--title", help="--book auto 时覆盖书名")
    ap.add_argument("--author", help="--book auto 时覆盖作者")
    ap.add_argument("--publisher", default="")
    ap.add_argument("--quote-page", default="")
    ap.add_argument("--tag", default="")
    ap.add_argument("--out", default="metadata/plan.json")
    ap.add_argument("--markdown", default="05-shot-plan.md")
    ap.add_argument("--sheet", help="可选：按顺序覆盖每镜的文案/版式（JSON 数组）")
    ap.add_argument("--theme", default="paper", help="huashu 8 套色板之一；同片只用一套")
    ap.add_argument("--account", default="")
    a = ap.parse_args()

    body = read_script(Path(a.script))
    if a.book == "auto":
        # 只给文案时：书名从《…》推，作者/出版社可缺；**封面必须由调用方给一个真实文件**
        m = re.search(r"《([^》]{1,30})》", body)
        title = a.title or (m.group(1) if m else "")
        if not title:
            die("--book auto：文案里找不到《书名》，也没有 --title")
        if not a.cover:
            die("--book auto 需要 --cover <真实书封路径>：书单号的书封是转化资产，缺封面必须阻塞（D16）。"
                "要么给封面，要么先跑 01 核验；不允许模型生成封面")
        if not Path(a.cover).exists():
            die(f"书封文件不存在：{a.cover}（回 01 拿真实封面；不允许模型生成，也不允许用占位图冒充）")
        book = {"title": title, "author": a.author or "", "publisher": a.publisher,
                "cover": a.cover, "cover_verified": True, "quote_page": a.quote_page, "tag": a.tag}
    else:
        book = json.loads(Path(a.book).read_text(encoding="utf-8"))
        for k in ("title", "author", "cover"):
            if not book.get(k):
                die(f"{a.book} 缺 {k}（书封必须是 01 阶段核验过的真实文件路径）")
        if not Path(book["cover"]).exists():
            die(f"书封文件不存在：{book['cover']}（回 01 重新核验，不许用模型生成的封面）")
    sheet = json.loads(Path(a.sheet).read_text(encoding="utf-8")) if a.sheet else []
    sents = sentences(body)
    total = ffprobe_duration(Path(a.audio))
    if not (10 <= total <= 900):
        die(f"主音轨时长 {total:.1f}s 不在 10–900s，先查 04 是否漏了尾句或 CTA")

    # 文案与音轨必须是一份：按 3–5 字/秒估算，偏差过大说明拿错了音轨或漏了半篇（会在 05 就报错，不拖到成片）
    chars = sum(len(re.sub(r"\s", "", s)) for s in sents)
    rate = chars / max(1e-6, total)
    if not (1.5 <= rate <= 6.5):
        die(f"文案 {chars} 字 / 音轨 {total:.1f}s = {rate:.1f} 字每秒，不像同一份稿（正常 3–5）。"
            f"查 04 是否用了旧音轨，或 02 是否漏了段落")
    # 镜数上限：每镜至少 5.5s（引文镜单独占一镜）。句子多就并句，不硬切成 4s 碎镜。
    # 镜数：短片（<35s）按 4.8s 一镜（保住内容不丢），长片按 6s 一镜（默认节奏 6–8s，避免一串 5s 碎镜）
    div = 4.8 if total < 35 else 6.0
    n_cap = len(sheet) if sheet else max(1, int(total / div))
    sents = group_sentences(sents, n_cap)
    weights = [len(re.sub(r"\s", "", s)) for s in sents]
    durations = split_weight(weights, total - 0.02, min(MIN_D, max(4.6, (total - 0.02) / len(sents) - 0.4)), MAX_D)
    if abs(sum(durations) - (total - 0.02)) > 0.3:      # 句子太多、每镜都到下限：允许改下限再把时长对齐
        durations = split_weight(weights, total - 0.02, max(2.0, (total - 0.02) / len(sents) - 0.5), MAX_D)
    shots, t = [], 0.0
    for i, (s, d) in enumerate(zip(sents, durations)):
        shots.append(build_shot(i + 1, s, d, t))
        t += d
    assign(shots, book, sheet, total - 0.02)
    for i, sh in enumerate(shots):
        if i < len(sheet):
            sh["_ov"] = sheet[i]
        make_spec(sh, book, a.theme)
        sh.pop("_ov", None)
        sh.pop("text", None)

    account = Path(a.account).stem if a.account else ""      # 只留账号名：成片文件名用得上，别把路径拼进去
    plan = {**PIPELINE, "theme": a.theme, "account": account, "audio": a.audio,
            "audio_duration": round(total, 3), "shot_count": len(shots), "shots": shots}
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    md = ["# 05 分镜计划", "", f"- 音轨：`{a.audio}` · {total:.2f}s · {len(shots)} 镜 · 色板 `{a.theme}`",
          f"- plan.json：`{out}`", "", "| # | 起 | 秒 | 语法 | 这一镜在做什么（物 + 动词） | 屏上字 | 书封 |",
          "|---|---|---|---|---|---|---|"]
    for sh in shots:
        cue = sh["spec"]["cues"][0]
        words = cue.get("text") or (cue.get("data", {}).get("title")) or ""
        act = {"bl_cover_hero": "书封升起，一句话压上去", "bl_quote": "引文逐行写出，出处落定",
               "t3_finance_chart": "柱子从 0 长出来，只标一处", "y2_vox": "真实素材满幅，笔圈住重点",
               "y5_kinetic_type": "主词砸入，辅句升起"}[sh["grammar"]]
        md.append(f"| {sh['id']} | {sh['start']:.1f}s | {sh['duration']:.1f} | `{sh['grammar']}` | {act} | {words} | {'✓' if sh['book_cover_required'] else ''} |")
    md += ["", "## 闸门", "下一步必须跑 `ours/lint_spec.py`：cue 白名单、边缘半字、文本截断、配比四条全绿才允许渲染。",
           "任何一镜改文案后，只重跑受影响的镜（`render_batch.py --only <id>`），不重渲全片。", ""]
    Path(a.markdown).write_text("\n".join(md), encoding="utf-8")
    print(f"✓ plan.json {len(shots)} 镜 · 总时长 {sum(s['duration'] for s in shots):.2f}s / 音轨 {total:.2f}s → {out}")
    print(f"✓ {a.markdown}")


if __name__ == "__main__":
    main()
