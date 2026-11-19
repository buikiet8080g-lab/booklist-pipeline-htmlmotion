#!/usr/bin/env python3
"""07 渲染：plan.json → clips/<id>.mp4 → render/master-noaudio.mp4。

只做编排，不改 vendor：每一镜写成 metadata/specs/<id>.json，调 `vendor/.../render.py --spec`，一路进程渲一镜。
特性（对应 §10）：
  · 输入签名复用：spec 内容 + 素材 sha256 + 画布/fps 一致就跳过（T10 断点续跑）
  · 失败隔离：某镜崩了记 status=failed 继续渲别的；全片 concat 只在没有失败镜时进行（T4）
  · 单镜返工：--only 003-1 只重渲这一镜，其他 mp4 的 mtime 不动（T3）
  · 并发：--parallel 3（T9）

用法：
  python3 ours/render_batch.py metadata/plan.json --workspace <项目> [--parallel 3] [--only 003-1,007-1] [--force]
"""
from __future__ import annotations

import argparse, hashlib, json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "vendor" / "huashu-art-motion" / "scripts" / "engine" / "render.py"
CANVAS = {"width": 720, "height": 1280, "fps": 24}


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def spec_for(shot: dict, plan: dict, ws: Path) -> dict:
    spec = {k: shot[k] for k in ("spec",) if k in shot}
    body = {"grammar": shot["grammar"], "duration": shot["duration"], "fps": CANVAS["fps"],
            "width": CANVAS["width"], "height": CANVAS["height"],
            "theme": shot.get("theme") or plan.get("theme"),
            "safe": shot.get("safe") or {"top": 80, "bottom": 300}}
    inner = shot.get("spec") or {}
    if "data" in inner:
        body["data"] = inner["data"]
    body["cues"] = inner.get("cues", [])

    def abspath(p: str) -> str:
        q = Path(p)
        return str((q if q.is_absolute() else (ws / q)).resolve())

    for c in body["cues"]:
        if c.get("image"):
            c["image"] = abspath(c["image"])
        if isinstance(c.get("frames"), str):
            c["frames"] = abspath(c["frames"])
    if isinstance(body.get("data"), dict) and body["data"].get("image"):
        body["data"]["image"] = abspath(body["data"]["image"])
    return body


def engine_fingerprint(grammar: str) -> str:
    """语法文件 + clip.js 的内容指纹：改了 patch 或 vendor 升级后，签名变化 → 自动重渲（T10）。"""
    h = hashlib.sha256()
    for f in (RENDER.parent / "clip.js", RENDER.parent / "clips" / f"{grammar}.js"):
        if f.exists():
            h.update(sha_file(f).encode())
    return h.hexdigest()[:8]


def signature(spec: dict, ws: Path) -> str:
    assets = []
    for c in spec["cues"]:
        for k in ("image", "frames"):
            v = c.get(k)
            if isinstance(v, str) and Path(v).is_file():
                assets.append([Path(v).name, sha_file(Path(v))])
    blob = json.dumps({**spec, "assets": sorted(assets), "canvas": CANVAS,
                       "engine": engine_fingerprint(spec.get("grammar", ""))}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True)
    if out.returncode != 0:
        return {}
    d = json.loads(out.stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    return {"w": s.get("width"), "h": s.get("height"), "fps": s.get("r_frame_rate"),
            "frames": s.get("nb_frames"), "duration": float((d.get("format") or {}).get("duration", 0) or 0)}


def render_one(shot: dict, plan: dict, ws: Path, force: bool, old: dict) -> dict:
    sid = shot["id"]
    spec = spec_for(shot, plan, ws)
    specdir = ws / "metadata" / "specs"; specdir.mkdir(parents=True, exist_ok=True)
    specfile = specdir / f"{sid}.json"
    specfile.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    sig = signature(spec, ws)
    clip = ws / "clips" / f"{sid}.mp4"
    prev = old.get(sid) or {}
    if not force and clip.exists() and prev.get("signature") == sig and prev.get("status") == "ok":
        return {**prev, "skipped": True}
    clip.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cmd = [sys.executable, str(RENDER), "--spec", str(specfile), "--out", str(clip), "--crf", "18"]
    ok, err, attempts = False, "", 0
    for attempts in (1, 2, 3):                              # 失败最多重试 2 次
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and clip.exists():
            ok = True
            break
        err = (r.stderr or r.stdout or "").strip()[-1200:]
    rec = {"id": sid, "grammar": shot["grammar"], "signature": sig, "status": "ok" if ok else "failed",
           "capture_seconds": round(time.time() - t0, 2), "retries": max(0, attempts - 1),
           "spec": f"metadata/specs/{sid}.json", "error": "" if ok else err}
    if ok:
        rec["ffprobe"] = probe(clip)
        if rec["ffprobe"].get("w") != CANVAS["width"] or rec["ffprobe"].get("h") != CANVAS["height"]:
            rec["status"] = "failed"
            rec["error"] = f"输出画布不对：{rec['ffprobe']}"
        rec["sha256"] = sha_file(clip)
    return rec


def concat(ws: Path, ids: list[str]) -> Path:
    lst = ws / "render" / "concat.txt"
    lst.parent.mkdir(parents=True, exist_ok=True)
    lst.write_text("".join(f"file '{(ws / 'clips' / f'{i}.mp4').resolve()}'\n" for i in ids), encoding="utf-8")
    out = ws / "render" / "master-noaudio.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24", "-an", str(out)], check=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--only", help="逗号分隔的镜 id，只渲这些（单镜返工）")
    ap.add_argument("--force", action="store_true", help="忽略签名，强制重渲")
    a = ap.parse_args()
    ws = Path(a.workspace).resolve()
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    shots = plan["shots"]
    only = set(x.strip() for x in a.only.split(",")) if a.only else None
    todo = [s for s in shots if not only or s["id"] in only]
    if only:
        miss = only - {s["id"] for s in shots}
        if miss:
            print(f"✗ --only 里有不存在的镜：{sorted(miss)}", file=sys.stderr)
            return 2
    man_path = ws / "metadata" / "render-manifest.json"
    old = {r["id"]: r for r in json.loads(man_path.read_text(encoding="utf-8")).get("shots", [])} if man_path.exists() else {}
    print(f"渲染 {len(todo)}/{len(shots)} 镜 · 并发 {a.parallel} · 输出 {ws/'clips'}")
    recs, t0 = {}, time.time()
    with ThreadPoolExecutor(max_workers=max(1, a.parallel)) as ex:
        futs = {ex.submit(render_one, s, plan, ws, a.force, old): s for s in todo}
        for f in as_completed(futs):
            s = futs[f]
            try:
                rec = f.result()
            except Exception as e:                          # noqa: BLE001
                rec = {"id": s["id"], "grammar": s["grammar"], "status": "failed", "error": str(e)}
            recs[s["id"]] = rec
            print(f"  {'·' if rec.get('skipped') else ('✓' if rec['status']=='ok' else '✗')} {rec['id']} {rec['grammar']} "
                  f"{rec.get('capture_seconds','')}s {('skip' if rec.get('skipped') else rec['status'])}"
                  + (f"  {rec['error'][:120]}" if rec.get("error") else ""))
    for sid, r in old.items():
        recs.setdefault(sid, r)
    ordered = [recs[s["id"]] for s in shots if s["id"] in recs]
    failed = [r["id"] for r in ordered if r.get("status") != "ok"]
    master = None
    if not failed and len(ordered) == len(shots) and not only:
        master = concat(ws, [s["id"] for s in shots])
        print(f"✓ concat → {master}")
    elif failed:
        print(f"✗ {len(failed)} 镜失败（{', '.join(failed)}）：不 concat，其余镜已出片。修完用 --only 重渲这几镜", file=sys.stderr)
    man = {"pipeline": "booklist-pipeline-htmlmotion", "canvas": "720x1280@24", "parallel": a.parallel,
           "rendered_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "total_seconds": round(time.time() - t0, 1),
           "shot_count": len(shots), "master": str(master) if master else "", "failed": failed,
           "shots": ordered}
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ manifest → {man_path}（{man['total_seconds']}s）")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
