# T21 · 30 秒样例（已验证）

这条样例用来证明流水线能出片，不是选题示范。**封面是排版占位图**：造 Skill 的环境只允许一次 git clone，
拿不到真实扫描封面，所以 `images/cover-demo.jpg` 上印着「DEMO COVER · 非真实扫描封面」。
生产必须换成 01 核验的真实封面（`metadata/book-assets.json` 里 `cover_verified: true`）。

## 成片

```
final/发布版-family-education-parent-reader-wood.mp4
25.60s · 720×1280 · 24fps · AAC 192k · ASS 字幕已烧
```

| 镜 | 语法 | 秒 | 内容 |
|---|---|---|---|
| 001-1 | `bl_cover_hero` | ~5 | 书封升起 + 书名/作者/豆瓣角标 |
| 002-1 | `y5_kinetic_type` | ~5 | 痛点句（忍住的那股劲）|
| 003-1 | `bl_quote` | ~7 | 书中引文「把孩子的课题还给孩子」+ 出处 |
| 004-1 | `y5_kinetic_type` | ~5 | 三页清单（先看见情绪 / 再说明规则 / 最后给选择）|
| 005-1 | `bl_cover_hero` | ~5 | CTA（橱窗在左下角） |

音轨：MiMo `茉莉`，25.60s。生成链路：`run_all.py --book metadata/book-assets.json`（35s 全自动：03 审核 → 04 配音 → 05 分镜 → lint → 07 渲染 → 08a 字幕对齐 → 08 出片）。

## 复跑

```bash
cd samples/t21-30s
python3 ../../ours/shot_plan.py --script 02-final-script.md --audio audio/main-voice.wav \
  --book metadata/book-assets.json --sheet metadata/sheet.json --theme wood \
  --account family-education-parent-reader --out metadata/plan.json --markdown 05-shot-plan.md
python3 ../../ours/lint_spec.py metadata/plan.json
python3 ../../ours/render_batch.py metadata/plan.json --workspace . --parallel 2
python3 ../../ours/assemble.py metadata/plan.json --workspace . \
  --account ../../accounts/family-education-parent-reader.md
```

## 抽帧结论（人工看过的）

| 帧 | 看什么 | 结论 |
|---|---|---|
| 3.0s | 书封占比与安全区 | 书封宽 410px（57% 画面宽）、高 730px（81% 内容带），整张不裁；标题与作者在内容带内，不进字幕区 |
| 9.0s | 引文 | 两行、字号 ≈80px、右侧留白 140px 不贴边；出处分两行「《被讨厌的勇气》/ 岸见一郎 · 第 88 页」不拆词 |
| 14.2s | y5 清单第 2 页 | 主词 + 辅句 + 进度轨 01/02/03，下半屏被背景序号填住，不空 |
| 16.6s | y5 清单第 3 页（深底页） | 文字清晰、进度轨 03 高亮、无叠字 |
| 19.5s | CTA | 角标「想读的点开」不出画、副标题「橱窗在左下角」在内容带内 |
| 全片 | 字幕 | 三行内、不溢出 720 宽、落在 1000–1230（不进正文区 y<980） |

## lint 结果

```
✓ lint_spec：0 红 / 8 黄 · 4 镜
```

8 个黄灯全是「已知且可接受」，逐条：

1. `W11` ×3：001/003/004 镜长 5.0–5.5s < 6s —— 整片只有 22.5s，4 句文案必须挤进 4 镜（正式片 ≥45s 时不会出现）。
2. `W07` / `W09` ×4：y5 背景巨型序号（12% 透明度装饰）与进度轨/辅句的外框重叠、右缘到 678px —— 上游 y5 的设计，抽帧确认视觉可读，不当叠字处理。
3. `W10` ×1：y5 深底页内容带覆盖率偏低 —— 文字型页面天然稀疏（阈值内）。

## 验收对照

| 项 | 结果 |
|---|---|
| T1 30 秒全链路 | ✓ 成片可播放，ffprobe 22.54s / 720×1280 / 24fps / AAC |
| T2 确定性 | ✓ 同一镜渲两次 mp4 `md5` 一致（`a9e66e7d…`） |
| T3 单镜返工 | ✓ 改 003-1 文案后 `--only 003-1`，其余 3 镜 mtime 不变 |
| T4 失败隔离 | ✓ 给 003-1 塞非法 cue，只有它 failed，另 3 镜照出片且不 concat |
| T5 字幕安全区 | ✓ 场景文字全在 y<980（生成器约束）；字幕落 1000–1230 |
| T7 时长对齐 | ✓ 22.54s vs 音轨 22.56s，差 0.02s |
| T10 断点续跑 | ✓ 原样再跑一遍：4/4 skip |
| T13 非法 cue 红灯 | ✓ y5 写 `kind:"quote"` → 启动失败 + lint 红 |
| T20 环境自检 | ✓ `env_check.py` 11/11 |
| T21 | ✓ 本页 |
| T6 / T8 / T9 / T11 / T12 / T14–T19 | 记录见 `SKILL.md`「已验证」与 `references/07`（T11 五语法抽帧结论 / T12 新语法 / T16–T17 补丁纯净与重放 / T18 风格配方不越界） |
