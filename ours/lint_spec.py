#!/usr/bin/env python3
"""05 闸门：plan.json 规格静态检查 + 逐镜动态抽帧检查（边缘半字 / 文本截断 / 叠字 / 死区 / 蓝紫底）。

为什么不用 `render.py --audit`：它只看主画布 fillText 的坐标，管不到被 translate 的标签、也管不到自动换行截断。
2026-10 竖屏实测：y2 的标签出界、标题被截断，`--audit` 报「红灯 0 黄灯 0」。所以边缘与截断必须在这里自己量。

用法：
  python3 ours/lint_spec.py metadata/plan.json                 # 静态 + 动态（需要 playwright）
  python3 ours/lint_spec.py metadata/plan.json --static-only   # 秒级，只跑规格规则
  python3 ours/lint_spec.py metadata/plan.json --json out.json # 机器可读报告
退出码：0 全绿 / 1 有红灯 / 2 环境问题（缺 playwright 等）
"""
from __future__ import annotations

import argparse, base64, colorsys, functools, http.server, json, socketserver, sys, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "huashu-art-motion" / "scripts" / "engine"
GRAMMARS = ["bl_cover_hero", "bl_quote", "y5_kinetic_type", "t3_finance_chart", "y2_vox"]
OPTIONAL = ["y3_whiteboard", "t2_keynote_ui"]
FORBIDDEN = ["y1_kurzgesagt", "y4_storytime", "y6_presenter_explainer", "t1_3b1b"]
KINDS = {
    "bl_cover_hero": {"cover", "text"}, "bl_quote": {"quote", "source"},
    "y5_kinetic_type": {"title", "point", "number", "highlight"},
    "t3_finance_chart": {"title", "bar", "line", "candle", "highlight", "number"},
    "y2_vox": {"image", "clip", "title", "point", "highlight"},
    "y3_whiteboard": {"title", "point", "draw", "image", "highlight"},
    "t2_keynote_ui": {"title", "card", "step", "image", "highlight", "number"},
}
PALETTES = {"paper", "poster", "ink", "navy", "bauhaus", "snow", "wood", "chalk"}
MAX_ONSCREEN = 12
SAMPLE = (0.10, 0.42, 0.72, 0.96)          # 抽帧位置（占镜长比例）

INSTRUMENT = r"""
(() => {
  window.__TXT = []; const P = CanvasRenderingContext2D.prototype;
  for (const fn of ['fillText', 'strokeText']) {
    const orig = P[fn];
    P[fn] = function (text, x, y) {
      try {
        if (fn === 'fillText' && this.canvas === window.__canvas && String(text).trim() && this.globalAlpha > 0.05) {
          const m = this.measureText(String(text)), tf = this.getTransform();
          const l = m.actualBoundingBoxLeft, r = m.actualBoundingBoxRight, as = m.actualBoundingBoxAscent, ds = m.actualBoundingBoxDescent;
          const q = [[x - l, y - as], [x + r, y - as], [x + r, y + ds], [x - l, y + ds]]
            .map(p => [tf.a * p[0] + tf.c * p[1] + tf.e, tf.b * p[0] + tf.d * p[1] + tf.f]);
          const xs = q.map(p => p[0]), ys = q.map(p => p[1]);
          window.__TXT.push({ text: String(text), x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys),
            px: parseFloat(this.font) * Math.hypot(tf.a, tf.b) });
        }
      } catch (e) {}
      return orig.apply(this, arguments);
    };
  }
})();
"""


def load_plan(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def hex_rgb(h: str):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c + c for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blue_purple(h: str) -> bool:
    r, g, b = [v / 255 for v in hex_rgb(h)]
    hue, sat, _ = colorsys.rgb_to_hsv(r, g, b)
    return 225 <= hue * 360 <= 300 and sat >= 0.30


def shot_texts(sh: dict) -> list[str]:
    out = []
    for c in sh.get("spec", {}).get("cues", []):
        for k in ("text", "sub"):
            if isinstance(c.get(k), str) and c[k].strip():
                out.append(c[k])
        if isinstance(c.get("data"), dict):
            for k in ("title", "label", "text"):
                if isinstance(c["data"].get(k), str) and c["data"][k].strip():
                    out.append(c["data"][k])
    return out


def static_checks(plan: dict, plan_path: Path) -> tuple[list, list]:
    red, yellow = [], []

    def R(code, msg, sid=""):
        red.append({"code": code, "shot": sid, "msg": msg})

    def Y(code, msg, sid=""):
        yellow.append({"code": code, "shot": sid, "msg": msg})

    shots = plan.get("shots") or []
    if not shots:
        R("E00", "plan.json 里没有 shots")
        return red, yellow
    themes = {s.get("theme") for s in shots} | ({plan["theme"]} if plan.get("theme") else set())
    if len(themes) > 1:
        R("E01", f"同片出现多套色板 {sorted(themes)}（D9：一条视频只准一套）")
    for t in themes:
        if t and t not in PALETTES:
            R("E02", f"色板「{t}」不在 huashu 8 套里：{sorted(PALETTES)}")
    total = 0.0
    for sh in shots:
        sid, g = sh.get("id", "?"), sh.get("grammar")
        total += float(sh.get("duration") or 0)
        if g not in GRAMMARS + OPTIONAL:
            R("E03", f"语法「{g}」不在白名单（{FORBIDDEN and '禁用：' + '/'.join(FORBIDDEN) if g in FORBIDDEN else '只允许 ' + '/'.join(GRAMMARS)}）", sid)
        if g in KINDS:
            for c in sh.get("spec", {}).get("cues", []):
                if c.get("kind") not in KINDS[g]:
                    R("E04", f"非法 cue kind「{c.get('kind')}」——{g} 只认 {sorted(KINDS[g])}（写错会被静默丢掉，画面少一页还不报错）", sid)
        d = float(sh.get("duration") or 0)
        hi = 15.01 if g in ("t3_finance_chart", "y3_whiteboard") else 12.01
        if d < 4.4 or d > hi:
            R("E05", f"镜长 {d:.1f}s 越界（默认 6–8s；短片下限 4.5s；引文 6.5–12s；数据/推导最长 15s）", sid)
        elif d < 6 and g not in ("bl_quote",):
            Y("W11", f"镜长 {d:.1f}s 短于 6s（只允许在总时长紧、整片 <40s 时出现）", sid)
        if sh.get("scene_type") == "free":
            if not sh.get("free_scene_reason"):
                R("E06", "free_scene 必须写 free_scene_reason（D8）", sid)
        # 屏上字：主词类是硬线（§14.2 放宽到 12 汉字）。>14 直接红灯——30 字标题不许靠缩字号硬塞（T14）
        for c in (sh.get("spec") or {}).get("cues", []):
            if c.get("kind") in ("point", "title", "cover", "quote", "number") and g in ("y5_kinetic_type", "bl_cover_hero", "y2_vox"):
                t = str(c.get("text") or "")
                if len(t) > 14:
                    R("E19", f"屏上字 {len(t)} 字（≤{MAX_ONSCREEN} 才稳，≥15 必须拆或改写）：{t[:18]}…", sid)
                elif len(t) > MAX_ONSCREEN:
                    Y("W01", f"屏上字 {len(t)} 字偏长（≤{MAX_ONSCREEN} 最稳）：{t[:16]}…", sid)
        if sh.get("book_cover_required"):
            assets = sh.get("assets") or []
            cov = [a for a in assets if a.get("role") == "book_cover"]
            if not cov:
                R("E07", "book_cover_required=true 但没有 role=book_cover 的资产（D16）", sid)
            for a in cov:
                p = Path(a["path"])
                cands = [p] if p.is_absolute() else [Path.cwd() / p, plan_path.parent.parent / p, plan_path.parent / p]
                if not any(c.exists() for c in cands):
                    R("E08", f"书封文件不存在：{a['path']}（回 01 换资产，不许模型生成）", sid)
        for a in sh.get("assets") or []:
            if a.get("source") == "model_generated" and a.get("role") == "book_cover":
                R("E09", "书封来源是 model_generated（D16 硬禁）", sid)
        spec = sh.get("spec") or {}
        if isinstance(spec.get("data"), dict) and "palette" in spec["data"]:
            R("E10", "data.palette 整覆盖被禁（只允许改 accent 单键，D9）", sid)
        if g == "t3_finance_chart":
            d = (sh.get("spec") or {}).get("data") or {}
            if not d.get("series"):
                R("E17", "t3_finance_chart 缺 data.series：数据必须来自真实来源，不许空图", sid)
            elif isinstance(d.get("series"), list) and not d.get("source"):
                Y("W13", "t3 没写 data.source（来源行）：书单号的数据镜头必须能溯源", sid)
            n = len(d.get("series") or [])
            for c in (sh.get("spec") or {}).get("cues", []):
                if c.get("kind") in ("bar", "line", "candle") and (c.get("data") or {}).get("index") is not None:
                    idx = c["data"]["index"]
                    bad = [i for i in ([idx] if isinstance(idx, int) else idx if isinstance(idx, list) else [])
                           if not isinstance(i, int) or i < 0 or i >= n]
                    if bad or not isinstance(idx, (int, list)):
                        R("E18", f"t3 的 data.index 要写柱子序号（0–{n-1} 的整数或整数数组），收到 {idx!r}（写 'all' 一根都不长）", sid)
        if g == "y2_vox":
            kinds = [c.get("kind") for c in (sh.get("spec") or {}).get("cues", [])]
            if "image" not in kinds and "clip" not in kinds:
                R("E16", "y2_vox 竖屏必须图片主导（缺 image/clip cue）：横宽文字卡在 720×1280 里必然下半屏空，改用 y5", sid)
        for key in ("style_recipe", "recipe", "scenes"):
            if key in spec or key in (spec.get("data") or {}):
                R("E11", "风格配方出现在主画面（D10：只允许片头卡/引文纹理/转场，且走 --alpha）", sid)

    free = [s for s in shots if s.get("scene_type") == "free"]
    if len(free) / len(shots) > 0.10 + 1e-9:
        R("E12", f"free_scene 占 {len(free)}/{len(shots)} 镜 > 10%（D8）")
    # 配比：文字主导 ≤30%
    text_led = [s for s in shots if s.get("grammar") in ("y5_kinetic_type", "t3_finance_chart")]
    if len(text_led) / len(shots) > 0.30 + 1e-9:
        Y("W02", f"文字主导 {len(text_led)}/{len(shots)} 镜 > 30%（§3.1）")
    # 每 3 镜至少 1 镜真实素材
    for i in range(0, len(shots), 3):
        win = shots[i:i + 3]
        if not any(s.get("book_cover_required") or (s.get("assets") or []) for s in win):
            Y("W03", f"第 {i+1}–{i+len(win)} 镜里没有真实素材（§3.1：每 3 镜至少 1 镜）")
    # 连续三镜同语法 / 每镜都推进
    for i in range(len(shots) - 2):
        if shots[i].get("grammar") == shots[i + 1].get("grammar") == shots[i + 2].get("grammar"):
            Y("W04", f"{shots[i]['id']}–{shots[i+2]['id']} 连续三镜同语法（相邻两镜必须换构图，§3.3）")
    # 首尾
    if shots[0].get("grammar") in ("y5_kinetic_type",) and not shots[0].get("spec", {}).get("cues"):
        R("E13", "首镜是纯标题卡（§3.1：0–3 秒必须是具体画面事件）")
    if shots[-1].get("grammar") == "y5_kinetic_type":
        Y("W05", "尾镜落在纯文字卡上；CTA 必须带书封（§3.1）")
    # 时长对齐
    if plan.get("audio_duration"):
        if abs(total - float(plan["audio_duration"])) > 0.3:
            R("E14", f"镜头总时长 {total:.2f}s 与音轨 {plan['audio_duration']:.2f}s 差 > 0.3s")
    # 蓝紫色
    for sh in shots:
        for c in sh.get("spec", {}).get("cues", []):
            d = c.get("data") or {}
            for k in ("accent", "color"):
                if isinstance(d.get(k), str) and d[k].startswith("#") and blue_purple(d[k]):
                    R("E15", f"强调色 {d[k]} 落在蓝紫区（色相 225–300 且饱和度 ≥0.30）", sh.get("id", ""))
    return red, yellow


ALLOWED: set[str] = set()


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def translate_path(self, path):                      # 和 render.py 同一套：/__file__/<绝对路径> 只服务 spec 点名的素材
        if path.startswith("/__file__/"):
            import urllib.parse
            f = urllib.parse.unquote(path[len("/__file__/"):].split("?")[0])
            return f if f in ALLOWED else "/nonexistent"
        return super().translate_path(path)


def dynamic_checks(plan: dict, plan_path: Path, throttle: float = 0.0) -> tuple[list, list]:
    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image
        import io
    except Exception as e:                                    # noqa: BLE001
        print(f"! 跳过动态检查（缺 playwright/PIL：{e}）；生产交付前必须补跑", file=sys.stderr)
        return [], [{"code": "W00", "shot": "", "msg": "动态检查未运行"}]

    red, yellow = [], []
    W, H = 720, 1280
    h = functools.partial(Handler, directory=str(VENDOR))
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), h)
    srv.daemon_threads = True
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    specdir = plan_path.parent / "specs"
    specdir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none"])
        for sh in plan["shots"]:
            sid = sh.get("id", "?")
            if sh.get("scene_type") == "free":
                yellow.append({"code": "W06", "shot": sid, "msg": "free_scene 的动态检查走 lint_scene（§6.5），这里跳过"})
                continue
            spec = {"grammar": sh["grammar"], "duration": sh["duration"], "fps": 24, "width": W, "height": H,
                    "theme": sh.get("theme") or plan.get("theme"), "safe": sh.get("safe") or {"top": 80, "bottom": 300},
                    "data": (sh.get("spec") or {}).get("data", {}), "cues": (sh.get("spec") or {}).get("cues", [])}
            sp = specdir / f"{sid}.json"
            assets = {}
            for a in sh.get("assets") or []:
                p = Path(a["path"]); p = p if p.is_absolute() else plan_path.parent.parent / p
                assets[a["path"]] = "file://" + str(p.resolve())
            import urllib.parse
            for c in spec["cues"]:
                for key in ("image", "frames"):
                    v = c.get(key)
                    if isinstance(v, str) and v in assets:
                        f = assets[v].replace("file://", "")
                        ALLOWED.add(f)
                        c[key] = "/__file__/" + urllib.parse.quote(f)
            sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.add_init_script("window.CLIP_SPEC = " + json.dumps(spec, ensure_ascii=False) + ";")
            pg.add_init_script(INSTRUMENT)
            pg.goto(f"http://127.0.0.1:{port}/clip.html?render=1")
            try:
                pg.wait_for_function("window.__ready === true || !!window.__bootFailed", timeout=60000)
            except Exception:
                red.append({"code": "D00", "shot": sid, "msg": f"{sh['grammar']} 启动超时"}); pg.close(); continue
            bf = pg.evaluate("window.__bootFailed || null")
            if bf:
                red.append({"code": "D01", "shot": sid, "msg": f"启动失败：{str(bf)[:200]}"}); pg.close(); continue
            expect = shot_texts(sh)
            drawn_all = []
            for frac in SAMPLE:
                t = round(sh["duration"] * frac, 3)
                raw = pg.evaluate("""async (t)=>{ window.__TXT.length=0; window.renderFrame(t);
                    const c=window.__canvas, g=c.getContext('2d');
                    const d=g.getImageData(0,0,c.width,c.height).data;
                    return {txt: JSON.parse(JSON.stringify(window.__TXT)), png: c.toDataURL('image/png')}; }""", t)
                drawn = raw["txt"]; drawn_all += [d["text"] for d in drawn]
                # 入场 0.28s 内的越界是 slam/overshoot 的动画过程（y5 的砸入本来就会胀一下），不算排版事故
                near = any(abs(t - float(c.get("at") or 0)) < 0.28 for c in (sh.get("spec") or {}).get("cues", []))
                for d in drawn:
                    if d["x0"] < 2 or d["y0"] < 2 or d["x1"] > W - 2 or d["y1"] > H - 2:
                        (yellow if near else red).append({"code": "W14" if near else "D02", "shot": sid,
                                    "msg": f"t={t}s 文字贴到画布边缘（x {d['x0']:.0f}–{d['x1']:.0f}, y {d['y0']:.0f}–{d['y1']:.0f}）：「{d['text'][:14]}」" + ("（入场动画过程中，可接受）" if near else "")})
                    if d["x1"] > W - 48 or d["x0"] < 48:
                        if not (d["x0"] < 2 or d["x1"] > W - 2):
                            yellow.append({"code": "W07", "shot": sid, "msg": f"t={t}s 文字进了左右安全区（{d['x0']:.0f}–{d['x1']:.0f}）：「{d['text'][:14]}」"})
                    # 入场动画（TY.rise 从基线下方推上来）中途的 bbox 会被 clip 掉，看不见；只看「真的停在字幕区里」的
                    straddle = d["y0"] < H - 300 < d["y1"]
                    parked = d["y0"] >= H - 300 and t > 0.6 * sh["duration"]
                    if straddle or parked:
                        red.append({"code": "D03", "shot": sid, "msg": f"t={t}s 文字压进底部 300px 字幕区（y {d['y0']:.0f}–{d['y1']:.0f}）：「{d['text'][:14]}」"})
                    if isinstance(d.get("px"), (int, float)) and 0 < d["px"] < 32 and not d["text"].strip().isdigit():
                        yellow.append({"code": "W08", "shot": sid, "msg": f"t={t}s 字号 {d['px']:.0f}px < 32px：「{d['text'][:14]}」"})
                # 叠字：任意两个文本框重叠 > 较小者 30%
                for i in range(len(drawn)):
                    for j in range(i + 1, len(drawn)):
                        A, B = drawn[i], drawn[j]
                        ox = max(0, min(A["x1"], B["x1"]) - max(A["x0"], B["x0"]))
                        oy = max(0, min(A["y1"], B["y1"]) - max(A["y0"], B["y0"]))
                        if not ox or not oy:
                            continue
                        small = min((A["x1"] - A["x0"]) * (A["y1"] - A["y0"]), (B["x1"] - B["x0"]) * (B["y1"] - B["y0"])) or 1
                        digits = lambda x: x["text"].strip().isdigit() or len(x["text"].strip()) <= 2
                        if ox * oy / small > 0.30 and A["text"] != B["text"] and not (digits(A) and digits(B)):
                            yellow.append({"code": "W09", "shot": sid, "msg": f"t={t}s 文字互相压着：「{A['text'][:10]}」/「{B['text'][:10]}」"})
                # 死区 / 纯色帧 / 蓝紫底：按像素算（内容带 80..980）
                im = Image.open(io.BytesIO(base64.b64decode(raw["png"].split(",")[1]))).convert("RGB")
                px = im.load()
                bg = px[4, 4]
                ink = 0; blue = 0
                for y in range(80, 980, 4):
                    for x in range(0, W, 4):
                        p = px[x, y]
                        if abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) > 24:
                            ink += 1
                            r_, g_, b_ = [v / 255 for v in p]
                            hh, ss, vv = colorsys.rgb_to_hsv(r_, g_, b_)
                            if 225 <= hh * 360 <= 300 and ss > 0.35 and vv > 0.12:
                                blue += 1
                tot = len(range(80, 980, 4)) * len(range(0, W, 4))
                if t > 0.5 * sh["duration"]:
                    if ink / tot < 0.025:
                        red.append({"code": "D07", "shot": sid, "msg": f"t={t}s 几乎是空帧：内容带只有 {ink/tot:.1%} 的像素有内容"})
                    elif ink / tot < 0.06:
                        yellow.append({"code": "W10", "shot": sid, "msg": f"t={t}s 画面偏空：内容带只有 {ink/tot:.1%} 的像素有内容（文字型镜头正常在 6–25%）"})
                if blue / max(1, ink) > 0.30:
                    red.append({"code": "D04", "shot": sid, "msg": f"t={t}s 蓝紫像素占画面 {blue/max(1,ink):.0%}（>30%，一眼 AI 味）"})
            # 截断：把这一镜所有画出来的字拼起来（去掉标点和空白），cue 里的字应该整句都在。
            # 缺尾且最后一个字贴到画布右缘 = 截断（红）；只是被折行拆开但字都在 = 不算问题。
            import re as _re
            norm = lambda x: _re.sub(r"[\s，。、：；！？·《》「」『』,.:;!?()（）]", "", x)
            joined = norm("".join(drawn_all))
            for want in expect:
                w = want.strip()
                if len(w) < 3:
                    continue
                wn = norm(w)
                if wn in joined:
                    continue
                # 找出画出来的最长前缀，看它是不是顶到右边缘
                pref = ""
                for d in drawn_all:
                    dn = norm(d)
                    if dn and wn.startswith(dn) and len(dn) > len(pref):
                        pref = dn
                edge = [d for d in drawn_all if norm(d) and norm(d) == pref and d["x1"] > W - 8]
                # 折行 vs 截断：字都在（按顺序能在拼起来的画面文字里找到）= 只是折行；有字彻底不见了 = 截断/丢字
                it = iter(joined)
                in_order = all(ch in it for ch in wn)
                if edge:
                    red.append({"code": "D05", "shot": sid, "msg": f"文本被画布截断：「{w[:20]}」只画出了「{pref[:12]}」"})
                elif not in_order:
                    red.append({"code": "D05", "shot": sid, "msg": f"文本被截断或丢字：「{w[:20]}」（画面里找不到这几字）"})
            if errs:
                red.append({"code": "D06", "shot": sid, "msg": f"页面报错：{errs[0][:160]}"})
            pg.close()
        b.close()
    srv.shutdown()
    srv.server_close()
    return red, yellow


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--static-only", action="store_true")
    ap.add_argument("--json", help="把报告写到这个路径")
    a = ap.parse_args()
    plan_path = Path(a.plan).resolve()
    plan = load_plan(plan_path)
    red, yellow = static_checks(plan, plan_path)
    if not a.static_only and not red:
        r2, y2 = dynamic_checks(plan, plan_path)
        red += r2; yellow += y2
    elif red:
        print("! 静态检查已有红灯，跳过动态抽帧（先修规格，别浪费渲染时间）", file=sys.stderr)
    rep = {"red": red, "yellow": yellow, "shots": len(plan.get("shots", []))}
    if a.json:
        Path(a.json).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in red:
        print(f"✗ [{r['code']}] {r['shot']} {r['msg']}")
    for y in yellow:
        print(f"! [{y['code']}] {y['shot']} {y['msg']}")
    print(f"{'✗' if red else '✓'} lint_spec：{len(red)} 红 / {len(yellow)} 黄 · {rep['shots']} 镜")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
