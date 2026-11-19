# 00 依赖与调用关系（实测核对，不靠印象）

## 一条命令的调用图

```
run_all.py
 ├─ 01 fetch_cover.py        urllib → book.douban.com / openlibrary.org（搜真实封面、校验、落盘）
 ├─ 02 rewrite_script.py     纯本地（1–N 篇文案 → 02-final-script.md）
 ├─ 03 audit_script.py       纯本地（口播性 + 对原稿覆盖率，红灯不进配音）
 ├─ 04 tts_mimo.py           subprocess → mimo-tts-generator/scripts/generate_mimo_tts.py → MiMo API
 ├─ 05 shot_plan.py          纯本地 + ffprobe（时长校验）
 ├─ lint lint_spec.py        Playwright → 本地 HTTP 打开 vendor/…/clip.html（抽帧量文字/像素）
 ├─ 07 render_batch.py       subprocess → vendor/…/render.py --spec（Playwright + Chromium + ffmpeg 编码）
 ├─ 08a align_subtitles.py   ffmpeg silencedetect（语音停顿 → 字幕时间）
 └─ 08b assemble.py          ffmpeg（混音 + ASS 烧录）+ ffprobe（QC）
```

## 用到的 / 没用到的（诚实清单）

| 组件 | 角色 | 谁调谁 | 真的用了吗 |
|---|---|---|---|
| **huashu-art-motion**（vendor，只读） | 渲染引擎：`clips/*.js` 语法 + `render.py` + 字体 | `render_batch.py` 起子进程跑 `render.py --spec`；`lint_spec.py` 用 Playwright 打开它的 `clip.html` | ✅ 用了（5 个语法的画面全部由它渲染） |
| **mimo-tts-generator** | 主音轨 | `tts_mimo.py` 起子进程调它的 `generate_mimo_tts.py`（它再走 MiMo API） | ✅ 用了（茉莉，77.8s 全片音轨） |
| **ffmpeg / ffprobe** | 编码、拼接、烧字幕、探测 | `tts_mimo` / `render_batch` / `align_subtitles` / `assemble` 直接 subprocess | ✅ 用了 |
| **Playwright + Chromium** | 无头渲染 + 像素级 lint | vendor `render.py`、`ours/lint_spec.py` | ✅ 用了 |
| **豆瓣 / OpenLibrary** | 按书名搜真实封面 | `ours/fetch_cover.py`（标准库 urllib，无 SDK） | ✅ 用了（豆瓣命中） |
| **MiMo API**（外网） | 语音合成 | 经 mimo skill 脚本 | ✅ 用了 |
| **apimart-image-generator** | 生成生活场景图（只给 `y2_vox` 镜用） | **本流水线没有调用它**：默认 `image_need=none`，两端都不出图 | ❌ 未使用 |
| **groq-subtitle-generator** | ASR 字幕 | 未安装、本机无 key；字幕改用 `ffmpeg silencedetect` 对齐 | ❌ 未使用 |
| **booklist-pipeline / Lite** | 阶段骨架、书封政策、九宫格切图 | 只迁移了 3 个独立脚本（`crop_grid_image` / `audit_book_cover_policy` / `image_provider_policy`），**主链不调用** | 备用 |

**没有任何视频生成模型**（dreamina / grok / 即梦 / HyperFrames / Remotion 都没接入），**没有 sub-agent**（pi 不支持）。

## 为什么图片工具没接进来

书单号的画面构成是：书封 + 引文 + 要点 + 数据 + CTA，全部由语法库画出来。
只有 `y2_vox`（照片/书页实拍 + 标注）需要真实图片素材，而这类镜在书单号里每片 ≤2 个，且优先用「书页实拍/截图」，不靠生成。
所以 `apimart-image-generator` 是**可选增强**，不是主链依赖：要接的话在 06 阶段调它出图，把路径写进 `plan.json` 的 `assets[]` / `y2` 的 `image` 即可（`references/06`）。

## 字幕为什么不用 ASR

本机没有 GROQ key，也没装 whisper。用户要的只是「字幕跟语音对上」：
`silencedetect` 找到语音停顿 → 把 02 的句子按字数落到每个说话段上，实测 4.0±0.3 字/秒、逐句贴合。
有 ASR 时用 `assemble.py --captions <asr.json>` 覆盖，接口留着。

## 外部依赖最小集（换机器要装什么）

```bash
python3 -m pip install playwright pillow     # 渲染 + 动态 lint
# Chromium：playwright install chromium（或复用已有 ~/.cache/ms-playwright）
ffmpeg / ffprobe                              # 6.x
# MiMo：skills/mimo-tts-generator/.env.local 里 MIMO_API_KEY
# 字体：vendor/…/lib/fonts/（随 vendor 自带，OFL）
python3 ours/env_check.py                     # 一条命令自检
```
