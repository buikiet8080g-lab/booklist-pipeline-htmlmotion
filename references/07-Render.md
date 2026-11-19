# 07 渲染（★核心）：vendor 调用 + patch 说明 + 竖屏三查

## 一句话

`plan.json` → 每镜一份 spec（`metadata/specs/<id>.json`）→ `vendor/.../render.py --spec` 出 `clips/<id>.mp4` → concat 出 `render/master-noaudio.mp4`。**我们不改 vendor，只编排**。

```bash
python3 <skill>/ours/render_batch.py metadata/plan.json --workspace . --parallel 3
python3 <skill>/ours/render_batch.py metadata/plan.json --workspace . --only 003-1     # 单镜返工
python3 <skill>/ours/render_batch.py metadata/plan.json --workspace . --force          # 忽略签名
```

| 机制 | 行为 | 对应验收 |
|---|---|---|
| 输入签名 | spec 内容 + 素材 sha256 + 画布/fps + **语法文件指纹**（patch 改了也会重渲） | T10 断点续跑 |
| 失败隔离 | 单镜最多重试 2 次，失败记 `status=failed` 继续其他镜；有失败镜就不 concat | T4 |
| 单镜返工 | `--only` 只碰指定镜，其他 mp4 的 mtime 不变 | T3 |
| 并发 | `--parallel 3`，每镜一路独立 chromium | T9 |
| manifest | 每镜 `ffprobe` / `capture_seconds` / `retries` / `sha256` / `signature` | 审计与复用 |

## 竖屏三查（每次改语法或改 patch 后都要做）

```bash
E=<skill>/vendor/huashu-art-motion/scripts/engine
python3 $E/render.py --spec /tmp/shot.json --out /tmp/stills --stills 0.5,2.5,5.5   # 抽 3 帧
python3 <skill>/ours/lint_spec.py metadata/plan.json                               # 动态段：边缘半字/截断/叠字/死区
```

1. **溢出**：内容（尤其书封、冲印件、标题）不许贴到画布四边 2px 内。
2. **截断**：cue 里的整句必须整句出现在画面里（折行可以，掉字不行）。
3. **死区**：内容带 `[80, 980]` 里空白 ≤20%（文字型镜头天然稀疏，见各语法的已知取舍）。

## 五个语法的竖屏结论（2026-10 实测，720×1280@24）

| 语法 | 结论 | 用法约束 |
|---|---|---|
| `y5_kinetic_type` | ✅ 主力，无溢出/截断 | 单页会显得空 → 竖屏用 **≥2 页清单**（进度轨 + 背景序号填下半屏）；**不要写 `data.label`**（竖屏标签会和主词重叠，叠字） |
| `t3_finance_chart` | ✅ 可用 | 图表占内容带上半，来源行与字幕带之间留 ~170px；底必须与相邻镜同色板 |
| `t2_keynote_ui`（optional） | ⚠️ 可用（打 0002 后死区 <10%） | 1–2 张卡最佳；3 张也行，卡片内留白偏多是大卡片的本性 |
| `y3_whiteboard`（optional） | ⚠️ 可用但中段留白 30–40% | 每片 ≤1 镜；≥4 条要点；不要单独当「金句镜」 |
| `y2_vox` | ⚠️ 只做图片主导 | 照片满幅（高 ≈86% 内容带）没问题；**文字卡在竖屏必然下半屏空**，文字用 y5 |
| `bl_quote`★ | ✅ 无溢出/截断 | 引文 ≤6 行；`data.key` 可以跨行（会自动按最长片段划）；出处自动两段式 |
| `bl_cover_hero`★ | ✅ 无溢出/截断 | 书封高 = 内容带 80%、宽 ≥55%；缺图直接启动失败；`data.tag` ≤8 字 |

## patch 与渲染的关系

`patches/0001–0006` 只在 vendor 上生效；`patches/apply.sh` 之后 `git status` 应恰好列出 11 个文件（9 改 + 2 新增）。
语法文件指纹进了签名，所以**打了新 patch 不需要 `--force`**，签名不同会自动重渲。

## 性能（本机 4 核）

| 场景 | 实测 |
|---|---|
| 单镜 5s（122 帧） | ≈5s（≈24 fps 抓帧，与规格书基准一致） |
| 4 镜 22.5s 并发 2 | 13–14s |
| 4 分钟片（30 镜，并发 3） | 推算 4–6 分钟（按单镜 5–8s 抓帧 + 编码） |

## 输出

```
clips/<id>.mp4                 # 每镜一条，硬切拼接
render/master-noaudio.mp4      # 无音轨母版（08 的输入）
metadata/specs/<id>.json       # 每镜实际送进 render.py 的 spec（审计/复现用）
metadata/render-manifest.json  # 每镜状态/耗时/签名/sha/ffprobe
```
