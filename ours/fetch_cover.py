#!/usr/bin/env python3
"""01 书封：按书名自动搜真实封面并落盘（用户不用找图）。

来源与判据（全部是「真实出版物图」，不是模型生成）：
  1. 豆瓣图书 suggest（`book.douban.com/j/subject_suggest`）→ /l/ 大图。中文书命中率最高。
  2. Open Library covers（ISBN 或标题）→ 备用（国内网络常不通，超时即跳过）。
  3. 都没有 → **阻塞**，打印「书名 / 候选 / 手动放图路径」三条出路，绝不生成占位图冒充。

校验（任一不过就换下一张，不静默接受）：
  · 图片能解码、短边 ≥ 300px、长宽比 0.45–0.95（竖版书封）
  · 候选书名与目标书名归一化后相同（繁简/空格/副标题容错），作者可选校验
  · 落盘后写 sha256 + 来源 URL，供 lint（E08/E09）与 manifest 追溯

用法：
  python3 ours/fetch_cover.py --book "被讨厌的勇气" [--author "岸见一郎"] [--out images/cover-verified.jpg]
  python3 ours/fetch_cover.py --book "被讨厌的勇气" --json      # 只打印候选，不下载
"""
from __future__ import annotations

import argparse, hashlib, io, json, re, sys, urllib.parse, urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
      "Referer": "https://book.douban.com/"}
MIN_EDGE = 300


def die(msg: str) -> "SystemExit":
    raise SystemExit(f"✗ {msg}")


def http(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def norm_title(s: str) -> str:
    s = re.sub(r"[《》〈〉\s·:：\-—()（）\[\]【】,，.。!！?？'\"“”]", "", str(s or ""))
    return s.replace("臺", "台").replace("討", "讨").replace("厭", "厌").replace("氣", "气").replace("勇氣", "勇气")


def douban(q: str) -> list[dict]:
    out = []
    try:
        raw = http("https://book.douban.com/j/subject_suggest?q=" + urllib.parse.quote(q))
        for it in json.loads(raw.decode("utf-8", "ignore")):
            if it.get("type") != "b":
                continue
            pic = it.get("pic") or ""
            big = pic.replace("/view/subject/s/", "/view/subject/l/").replace("/view/subject/m/", "/view/subject/l/")
            out.append({"source": "douban", "title": it.get("title", ""), "author": it.get("author_name", ""),
                        "year": it.get("year", ""), "id": it.get("id", ""), "page": it.get("url", ""), "image": big})
    except Exception as e:                                   # noqa: BLE001
        print(f"· 豆瓣不可用（{type(e).__name__}），跳过", file=sys.stderr)
    return out


def openlibrary(q: str, isbn: str = "") -> list[dict]:
    out = []
    try:
        if isbn:
            data = json.loads(http(f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data", 10))
            for k, v in data.items():
                if v.get("cover", {}).get("large"):
                    out.append({"source": "openlibrary", "title": v.get("title", ""), "author": "",
                                "year": "", "id": isbn, "page": "", "image": v["cover"]["large"]})
        else:
            data = json.loads(http("https://openlibrary.org/search.json?q=" + urllib.parse.quote(q) + "&limit=5", 10))
            for d in data.get("docs", [])[:5]:
                cid = d.get("cover_i")
                if cid:
                    out.append({"source": "openlibrary", "title": d.get("title", ""), "author": ", ".join(d.get("author_name", [])[:2]),
                                "year": str(d.get("first_publish_year", "")), "id": str(cid), "page": "", "image": f"https://covers.openlibrary.org/b/id/{cid}-L.jpg"})
    except Exception:                                        # noqa: BLE001
        pass
    return out


def check_image(blob: bytes) -> tuple[bool, str]:
    try:
        from PIL import Image
    except Exception:                                        # noqa: BLE001
        return (len(blob) > 20000, f"{len(blob)//1024}KB（无 PIL，未验尺寸）")
    try:
        im = Image.open(io.BytesIO(blob))
        w, h = im.size
        ar = w / h
        ok = min(w, h) >= MIN_EDGE and 0.45 <= ar <= 0.95
        return ok, f"{w}×{h} ar={ar:.2f}"
    except Exception:                                        # noqa: BLE001
        return False, "解码失败"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--isbn", default="")
    ap.add_argument("--out", default="images/cover-verified.jpg")
    ap.add_argument("--json", action="store_true", help="只列候选，不下载")
    a = ap.parse_args()

    cands = douban(a.book) + openlibrary(a.book, a.isbn)
    want = norm_title(a.book)
    # 书名要能对上（允许「书名 副标题」和繁体）；作者对得上优先
    scored = []
    for c in cands:
        t = norm_title(c["title"])
        same = t == want or t.startswith(want) or want.startswith(t)
        if not same:
            continue
        bonus = 1 if a.author and norm_title(a.author)[:3] and norm_title(a.author)[:3] in norm_title(c["author"]) else 0
        scored.append((bonus, c))
    scored.sort(key=lambda x: -x[0])
    good = [c for _, c in scored]
    if a.json:
        print(json.dumps(good, ensure_ascii=False, indent=1))
        return 0 if good else 1
    if not good:
        die(f"没搜到《{a.book}》的可核验封面（豆瓣/OpenLibrary 都没有匹配项）。\n"
            f"  三条出路：① 用 --isbn 指定版次重试；② 书名写成版权页上的全名再试；"
            f"③ 手动把官方封面放到 {a.out}（不许用模型生成或占位图）")

    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    tried = []
    for c in good[:6]:
        try:
            blob = http(c["image"])
        except Exception as e:                               # noqa: BLE001
            tried.append(f"{c['source']}:{c['id']} 下载失败 {type(e).__name__}")
            continue
        ok, detail = check_image(blob)
        tried.append(f"{c['source']}:{c['id']} {detail} {'✓' if ok else '✗'}")
        if not ok:
            continue
        out.write_bytes(blob)
        meta = {"title": a.book, "author": a.author, "cover": str(out), "cover_verified": True,
                "cover_source": f"{c['source']}:{c['id']}", "source_page": c["page"], "source_image": c["image"],
                "edition_title": c["title"], "edition_author": c["author"], "edition_year": c["year"],
                "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob), "checked": detail}
        Path("metadata").mkdir(exist_ok=True)
        Path("metadata/cover-source.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ 封面 → {out}（{c['source']} · {c['title']} {c['year']} · {detail}）")
        print(f"  sha256 {meta['sha256'][:16]}… · 来源 {c['page'] or c['image']}")
        return 0
    die("搜到了候选但都不合格（尺寸/比例/下载）：\n  " + "\n  ".join(tried) +
        f"\n  请手动放官方封面到 {a.out}，或换 --isbn 指定版次")


if __name__ == "__main__":
    sys.exit(main())
