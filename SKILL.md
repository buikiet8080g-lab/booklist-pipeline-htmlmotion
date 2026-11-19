---
name: booklist-pipeline-htmlmotion
description: 书单号视频一键成片流水线。用户只贴 1–N 篇同书文案 + 说书名：自动搜真实封面（豆瓣）、整合改写、MiMo 配音、按语音停顿对齐字幕、用 huashu 语法库逐帧渲染成 720x1280@24fps 竖屏成片（真实书封 + 书中引文 + 要点/数据 + CTA）。模型只写 JSON 规格，不写 HTML、不用视频生成模型、不用 FFmpeg 关键帧动效。用户要做书单号视频、卖书视频、多篇文案合成一条、或要求「用代码/语法库生成解释型竖屏视频」时使用；真人出镜、口型同步、剧情短片、横屏 16:9 不适用。
metadata:
  author: booklist
  version: "1.2.0"
---

# 书单号视频流水线 · huashu 语法库版

一台「会动的读书笔记」生产机：**模型写规格，代码画画面**。真实书封 + 书中引文 + 三层论证 + 数据 + CTA，逐帧渲染成 720×1280@24fps，硬切拼接。

```
（用户：贴文案 + 说书名）
01 自动搜封面 → 02 整合改写 → 04 MiMo 主音轨 → 05 plan.json
   → 06 素材（默认 none）→ 07 语法库渲染 → 08a 字幕对齐 → 08 烧录 + QC → 成片
03 文案审核可选（改写成熟文案时跳过）
```

## 一、这个 Skill 是什么 / 不是什么

| 是 | 不是 |
|---|---|
| 文本模型写 **JSON 规格**（每镜 10–20 行），vendor 语法库渲染 | 不是每镜写 HTML/CSS/JS（那是 `free_scene` 兜底，≤10%，必须写理由） |
| 逐帧确定性（`frame(t)=f(t)`），可单镜重渲、可逐帧比对 | 不用视频生成模型、不用 GSAP/Remotion、不用 CSS `@keyframes` |
| 真实书封 + 书中原文 + 数据/对比 | 不让模型生成封面，不在图片阶段贴图修补书封 |
| 会动的读书笔记 | 不是电影感素材片；不做真人出镜/口型/数字人 |

**诚实边界（别承诺做不到的）**

- 不做真人出镜 / 口型同步 / 数字人；要实拍感素材只能作为 `assets[].role=broll_slot` 由别的工具生产，本 Skill 只消费。
- 中文排版「干净可用」，不做标点悬挂、竖排、复杂避头尾。
- 复杂 3D / 粒子 / 物理仿真不保证；稳定区间是 2D 布局 + 变换 + 遮罩。
- 写规格也会出错，所以有 lint + 单镜重渲（出错成本 ≈ 5 秒），**不承诺一次写对**。
- 文案侧只做到「整合改写」（多篇同书文案合并去重 + 补 CTA）；**从零原创选题（`original`）未实现**，接口名保留。
- 机械整合不等于好文笔：要求文字质量时，由主 Agent 先按 `references/02` 的规则自己改写，再让流水线跑后半段。
- y3 白板 / t2 发布会是 optional：竖屏可用但 y3 中段留白 30–40%（白板本身是留白），每片 ≤1 镜。

## 二、10 条硬约束（违反即返工）

1. 主渲染路线 = huashu 语法库：`plan.json` → `ours/render_batch.py` → `render.py --spec`。**不要让模型每镜写 HTML**。
2. `vendor/huashu-art-motion/` 一个字节不改；所有改动只在 `patches/`（≤6 个，`git apply` 可重放）。
3. 语法白名单 5 个：`bl_cover_hero`★ / `bl_quote`★ / `y5_kinetic_type` / `t3_finance_chart` / `y2_vox`；optional `y3_whiteboard` / `t2_keynote_ui`；**禁用** `y1 y4 y6 t1`。
4. 白名单外 cue 必须红灯：huashu 原生会静默丢弃非法 cue（给 y5 写 `quote` 整页消失且不报错），靠 `patches/0006` + `ours/lint_spec.py` 双保险。
5. `render.py --audit` 有盲区（实测抓不到竖屏溢出/截断）：必须跑自写的「画布边缘半字检测」与「文本截断检测」（`lint_spec.py` 的动态段）。
6. 字幕绝不写进场景代码，统一后期 ASS 烧录；画面正文禁止进 `y ≥ 980`（底部 300px 归字幕）。
7. 书封只能用 01 核验的真实资产；禁模型生成封面；禁图片阶段贴图修补。
8. 同片只用一套色板（`paper/poster/ink/navy/bauhaus/snow/wood/chalk`）；禁 `data.palette` 整覆盖；禁蓝紫区（色相 225–300、饱和度 ≥0.30）。
9. 57 张风格配方**不进主画面**，只允许片头卡 / 引文纹理 / 转场三处，且必须 `--alpha` 合成。
10. 不照搬 Lite 的 T0 子代理铁律：pi 没有 sub-agent，主 Agent 直接生产，**用户确认点 0 个**（除真实阻塞）。

## 三、8 阶段与闸门

| 阶段 | 做什么 | 输入 → 输出 | 闸门 |
|---|---|---|---|
| 01 书封核验 | `ours/fetch_cover.py` 按书名搜真实封面（豆瓣 → OpenLibrary），校验书名/尺寸/比例后落盘并记来源与 sha256 | 书名 → `images/cover-verified.jpg`、`metadata/cover-source.json` | 搜不到或不合格 → 阻塞，绝不用占位图/模型图（`audit_book_cover_policy`） |
| 02 整合改写 | `ours/rewrite_script.py`：1–N 篇同书文案 → 去噪/去重/按分数保留/补 CTA；主 Agent 改写质量更高 | 贴的文案 → `02-final-script.md` + `02-rewrite-record.md` | CTA 有橱窗动作；字数/音轨 1.5–6.5 字每秒（05 核） |
| 03 内容审核（**硬闸门**） | `ours/audit_script.py`：覆盖率（原稿信息有没有丢）+ 句长 + 口语化/术语 + 对话感（你/问句）+ 数字是否被删 + 硬伤 | 02（+原稿）→ `03-script-audit.md`、`metadata/03-script-audit.json` | 覆盖率 <55%、句子 >32 字、通篇无「你」「问句」、丢 ≥3 个原稿数字、无 CTA → **红灯回 02** |
| 04 主音轨 | `ours/tts_mimo.py`：MiMo 分块并发 → 顺序拼接 | 02 → `audio/main-voice.wav`、`metadata/04-voice/*.json`、`04-audio.md` | 无漏尾漏 CTA；时长入档（T7 用它对齐）；无 key 直接报错不降级 |
| 05 分镜 | 文案+音轨时长 → 镜头、语法、秒数、字幕边界 | 02+04+01 → `metadata/plan.json`、`05-shot-plan.md` | `ours/shot_plan.py` 出片；**必须过 `lint_spec.py`** |
| 06 素材 | 默认 `image_need=none`；只有 y2/书封镜要图 | plan → `images/*`、`06-image-assets.md` | 书封槽位图必须来自 01；`audit_book_cover_policy` 通过 |
| 07 渲染 | 每镜一路进程 → clips → concat | plan → `clips/*.mp4`、`render/master-noaudio.mp4`、`metadata/render-manifest.json` | lint 全绿；空帧 = 0；竖屏三查（溢出/截断/死区） |
| 08 收尾 | `align_subtitles.py` 按语音停顿对齐字幕（默认）→ 混音 + ASS 烧录 + ffprobe QC | 07 + 04 → `metadata/captions.json`、`final/发布版-*.mp4`、`08-final-delivery.md` | 字幕贴语音（4±0.5 字/秒）；分辨率/帧率/音轨/时长 ≤0.5s；`final/` 只有一个成片 |

**用户只做两件事：贴文案（1–N 篇同书）+ 说书名。剩下的全自动**（搜封面→整合改写→配音→分镜→闸门→渲染→字幕后同步→出片）：

```bash
# 主 Agent 把用户贴的文案落到 sources/*.txt（用户不建文件），然后一条命令：
python3 <skill>/ours/run_all.py --book "被讨厌的勇气" --author "岸见一郎" \
    --sources sources/a.txt sources/b.txt \
    --account <skill>/accounts/family-education-parent-reader.md
# --book 只给书名 → 自动搜真实封面（豆瓣/OpenLibrary，校验书名+尺寸后落盘）
# 没有 02-final-script.md → 自动整合改写；已有则直接用
# 字幕自动按语音停顿对齐（不用参数、不用 key）；色板按账号取，--theme 可覆盖
```

质量更高的一条路：主 Agent 先按 `references/02` 的整合规则自己改写（比机械合并好），写到 `02-final-script.md`，再跑同一条命令（不带 `--sources`）。

分步命令（返工/调试时用）：

```bash
python3 <skill>/ours/shot_plan.py --script 02-final-script.md --audio audio/main-voice.wav \
    --book metadata/book-assets.json --sheet metadata/sheet.json --theme wood --out metadata/plan.json
python3 <skill>/ours/lint_spec.py metadata/plan.json          # 红灯不许进 07
python3 <skill>/ours/render_batch.py metadata/plan.json --workspace . --parallel 3
python3 <skill>/ours/assemble.py metadata/plan.json --workspace . --account <skill>/accounts/family-education-parent-reader.md
```

## 四、五个语法怎么选（详细正反例见 `references/09-Spec-Writing-Guide.md`）

| 语法 | 承载 | 一镜 | 每片 | 竖屏实测 |
|---|---|---|---|---|
| `bl_cover_hero` | 书封主打、CTA | 5–8s | 3–5 次 | 书封宽 ≥55% / 高 80% 内容带，整张不裁 |
| `bl_quote` | 书中原文引文 | 7–12s | 2–4 次 | 文楷衬线、88→40px 自适应、出处两段式不拆词 |
| `y5_kinetic_type` | 要点/清单/金句/数字 | 5–15s | 主力 | 单页会空 → **竖屏用 ≥2 页清单版式**（进度轨+序号填下半屏） |
| `t3_finance_chart` | 数据/对比/趋势 | 6–8s | 按需 | 底和相邻镜同色板；剩 20% 下图带留白，可接受 |
| `y2_vox` | 真实素材满幅 + 标注 | 6–10s | ≤5 镜 | **只做图片主导**：竖屏文字卡又宽又矮，下半屏必空 |

## 五、踩坑（都是实测踩过的，别再踩）

1. **`--audit` 报 0 红灯不等于没问题**：y2 的标签出界、标题截断，audit 全绿。所以 `lint_spec.py` 一定要跑动态段。
2. **写错 cue kind 会静默消失**：y5 没有 `quote` 原语。`patches/0006` 之后启动即失败。
3. **竖屏内容带很窄**：`u = min(W,H)/1080 = 0.667`。字号写 `40*u = 27px` 会低于 32px 下限；屏幕 px 与 `*u` 混用是竖屏最常见的排版事故。
4. **`NotoSerifSC-sub` 只含示范片用到的字**（实测缺「孩爱候他」），引文会回退系统黑体。`bl_quote` 改用 `LXGWWenKai-500`（GB2312 全字集）。
5. **`TY.rise` 入场时 bbox 会短暂落进字幕区，但被 clip 掉看不见**；判「文字压字幕区」要看是否 straddle 或动画落定后才算（`lint_spec` 已按这个判）。
6. **w 后缀字体（woff）不能给 libass 用**：ASS 字幕字体走系统 `WenQuanYi Zen Hei`，别指 `assets/fonts/*.woff`。
7. **playwright 版本要和缓存的 chromium 对齐**：本机缓存 1248、`pip install playwright` 默认要 1228 → `playwright install chromium`，或把 `chromium{,_headless_shell}-1228` 软链到 1248。字幕永远不进场景代码。

## 六、已验证（2026-10，本机 4 核）

- **样例（T21）**：`samples/t21-30s/final/发布版-family-education-parent-reader-wood.mp4`（25.60s，720×1280@24，AAC，ASS 已烧）。5 镜：`bl_cover_hero` → `y5` → `bl_quote` → `y5`（3 页清单）→ CTA；MiMo 茉莉真音轨；抽帧确认：书封整张不裁、书名/作者不进字幕区、引文两行不出界、进度轨 01/02/03 正常、字幕贴语音（4.1 字/秒）。
- **样例的封面是占位**：`images/cover-demo.jpg` 是排版生成的 DEMO 封面（书封上印着「非真实扫描封面」），因为造 Skill 的环境只允许一次 git clone、拿不到真实扫描件。生产必须换成 01 核验的真实封面，`lint_spec` 见 `cover_verified=false` 会报黄。
- **贴文案+说书名 全链路（2026-10 实测）**：2 篇同书文案 + 书名 → 自动搜封面（豆瓣 527×773）→ 改写 271 字 → 03 审核（覆盖率 84%、0 红）→ MiMo 77.8s 音轨 → 12 镜 → 字幕 16 条对齐 → 成片。全链路 112s，成片 77.7s、lint 0 红。
- 样例（`samples/t21-30s`）：单篇文案 90 字 → 03 审核 0 红 → 25.6s 成片 5 镜，全链路 35s。
- 03 审核反例：一篇 84 字、通篇「底层逻辑/赋能/闭环」的稿子 → 4 红（长句/黑话/无对话感/无 CTA）。
- 渲染速度：4 镜 22.5s（540 帧）并发 2 → **13–14s**；单镜 5s（122 帧）≈ 5s（≈24 fps 抓帧）。
- 确定性（T2）：同一镜渲两次 mp4 `md5` 一致；断点续跑（T10）再跑一遍 4/4 skip；单镜返工（T3）只改该镜 mtime；失败隔离（T4）非法 cue 只让那一镜失败、其余照出片。
- vendor 基线：`v1.2.0`（commit `8f0a349`），`scripts/engine` 24M，6 个 patch 顺序 apply 全绿。

### 验收 T1–T21 状态（诚实记录）

| 项 | 结果 |
|---|---|
| T1 30 秒全链路 | ✓ 成片 25.6s 可播放（`samples/t21-30s/final/…`，5 镜，03 审核 0 红） |
| T2 确定性 | ✓ 同镜渲两次 mp4 md5 一致 |
| T3 单镜返工 | ✓ 只有被改镜的 mtime 变化 |
| T4 失败隔离 | ✓ 非法 cue 只让 1 镜 failed，其余照出片、不 concat |
| T5 字幕安全区 | ✓ 场景文字全在 y<980（lint D03 红线）；字幕落 1000–1230 |
| T6 书封一致性 | ⚠ 部分：`lint` 校验书封存在 + 来源合规、manifest 记每镜 sha256；样例封面是占位图，与 01 资产一致的**正式**核验未做 |
| T7 时长对齐 | ✓ 25.58s vs 音轨 25.60s |
| T8 画风一致（grep 裸色值） | 不适用：场景代码不落地，颜色只来自 8 套色板（`lint` E01/E02/E15） |
| T9 4 分钟片性能 | ⚠ 未实测：只验了 4 镜 22.5s 并发 2 → 13–14s（按单镜 5–8s 推算 30 镜 4–6 分钟） |
| T10 断点续跑 | ✓ 原样重跑 4/4 skip |
| T11 五语法竖屏 | ✓ y5 / t3 / t2 / y2 / y3 各渲 8s 抽帧，结论见 `references/07` 的表（y3/t2 optional 有留白取舍） |
| T12 新语法 | ✓ bl_quote 衬线引文 + 出处；bl_cover_hero 书封占 57% 宽 / 81% 高 |
| T13 非法 cue 红灯 | ✓ y5 写 `quote` → 启动失败 + lint 红 |
| T14 超长标题红灯 | ✓ 30 字主词 → `lint` E19 红（不允许靠缩字号硬塞） |
| T15 fork 归属 | ✓ `NOTICE.md`（MIT + commit + 改动清单）+ `vendor/.../LICENSE` |
| T16 vendor 纯净 | ✓ 未 apply 时 `git status` 干净；apply 后恰好 11 个文件（9 改 + 2 新增） |
| T17 patch 可重放 | ✓ 从 `git archive HEAD` 的干净副本重放 6 个 patch，与原工作树 `diff -r` 一致 |
| T18 风格配方不越界 | ✓ 全片 spec 无 `recipe/style_recipe/scenes`（`lint` E11）；第一期不使用风格配方 |
| T19 账号风格一致 | ⚠ 两个账号已建档（`wood` / `paper` + 字幕样式），连续 3 条片的对比未做 |
| T20 环境自检 | ✓ `ours/env_check.py` 11/11 |
| T21 | ✓ 见上 |

## 七、机器可读 marker（产物里照抄）

```yaml
pipeline: booklist-pipeline-htmlmotion
pipeline_version: 1.2
render_engine: huashu_grammar_vendor
canvas: 720x1280@24
subtitle_safe_bottom_px: 300
vendor_baseline_tag: v1.2.0
vendor_readonly: true
patches_applied: [0001,0002,0003,0004,0005,0006]
grammar_whitelist: [bl_cover_hero, bl_quote, y5_kinetic_type, t3_finance_chart, y2_vox]
grammar_optional: [y3_whiteboard, t2_keynote_ui]
grammar_forbidden: [y1_kurzgesagt, y4_storytime, y6_presenter_explainer, t1_3b1b]
single_theme_per_video: true
data_palette_full_override_forbidden: true
blue_purple_zone_forbidden: "hue 225-300, sat>=0.30"
style_recipe_in_main_layer_forbidden: true
free_scene_max_ratio: 0.10
subtitle_in_scene_forbidden: true
ass_burn_in_post_only: true
video_model_used: false
ffmpeg_keyframe_motion_forbidden: true
subagent_required: false
user_confirmation_points: 0
```

## 七、和别的工具是什么关系（详见 `references/00-Dependencies.md`）

| 组件 | 谁调谁 | 用了吗 |
|---|---|---|
| huashu-art-motion（vendor） | `render_batch.py` 起子进程 `render.py --spec`；`lint_spec.py` 用 Playwright 开它的 `clip.html` | ✅ 全部画面 |
| mimo-tts-generator | `tts_mimo.py` 起子进程调它的脚本（再走 MiMo API） | ✅ 全片音轨 |
| ffmpeg / Playwright / 豆瓣 | 编排层直接调 | ✅ |
| apimart-image-generator | **未调用**：`image_need=none`，y2 镜才需要真实图 | ❌（可选增强） |
| groq-subtitle-generator | **未用**：无 key；字幕改 `ffmpeg silencedetect` 对齐 | ❌ |

全链不含视频生成模型、不含 sub-agent。

## 八、目录

```
booklist-pipeline-htmlmotion/
├── SKILL.md                     # 本文件（≤200 行）
├── vendor/huashu-art-motion/    # 上游 v1.2.0，只读；vendor/BASELINE.md 记基线
├── patches/                     # 唯一允许的改动：0001–0006 + apply.sh + README
├── ours/                        # 编排层：shot_plan / lint_spec / render_batch / assemble / env_check + 三个迁移脚本
├── references/01–09             # 阶段文档（09 = 五个语法的 cue 正反例）
├── accounts/                    # 账号人设 + visual_style_profile（5 层）
├── config/                      # theme-presets / grammar-presets / ebook-sources
├── assets/fonts/                # NotoSansSC ×4 + NotoSerifSC（引文用 vendor 的 LXGWWenKai）
├── workspace-template/          # 项目目录模板 + sheet.json / captions.json 示例
├── NOTICE.md                    # 上游归属（MIT / commit / 改动清单）
└── samples/t21-30s/             # T21 30 秒样例（成片 + plan + manifest + 抽帧结论）
```
