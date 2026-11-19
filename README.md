# booklist-pipeline-htmlmotion

书单号视频流水线：**模型写 JSON 规格，huashu 语法库逐帧渲染**成 720×1280@24fps 竖屏成片。
真实书封 + 书中原文引文 + 要点/对比/数据 + 收尾 CTA。不用视频生成模型、不用 FFmpeg 关键帧动效、不写 HTML。

主文档：[`SKILL.md`](SKILL.md)（≤200 行）。阶段细节：[`references/01–09`](references/)。

## 30 秒上手（贴文案 + 说书名）

用户只需要：**把 1–N 篇同书文案贴进来 + 说书名**。封面自动搜、文案自动整合、配音/分镜/字幕/渲染全自动。

```bash
S=~/.pi/agent/skills/booklist-pipeline-htmlmotion
python3 $S/ours/env_check.py                     # 环境自检（playwright/ffmpeg/vendor/字体）
mkdir -p /tmp/mybook/sources && cd /tmp/mybook
# 主 Agent 把用户贴的文案落到 sources/*.txt（用户不用建文件、不用找封面）
$EDITOR sources/a.txt sources/b.txt
python3 $S/ours/run_all.py --book "被讨厌的勇气" --author "岸见一郎" \
        --sources sources/a.txt sources/b.txt \
        --account $S/accounts/family-education-parent-reader.md
ls final/        # 发布版-*.mp4
```

`run_all.py` 依次跑：01 搜封面（豆瓣/OpenLibrary，校验书名与尺寸）→ 02 整合改写（多篇去重合并 + 补 CTA）→ **03 内容审核（覆盖率/句长/口语/对话感/数字保留，红灯停）** → 04 配音（MiMo 分块并发）→ 05 分镜（镜数与语法自动分配、y5 自动拆清单）→ lint 闸门 → 07 渲染 → 08a 字幕按语音停顿对齐 → 08 混音 + ASS 烧录 + QC。
任何一步失败就停在那一步，修完重跑同一条命令，已完成步骤自动跳过。

分步命令见 `references/04–08`（返工单镜、只重做字幕等）。

## 目录

| 路径 | 说明 |
|---|---|
| `vendor/huashu-art-motion/` | 上游只读副本，pin **v1.2.0**；基线见 [`vendor/BASELINE.md`](vendor/BASELINE.md) |
| `patches/` | 唯一允许的改动：`0001–0006` + `apply.sh`；说明见 [`patches/README.md`](patches/README.md) |
| `ours/` | 编排层：`shot_plan` / `lint_spec` / `render_batch` / `assemble` / `env_check` + 从 Lite 迁来的三个脚本 |
| `references/` | 00 依赖与调用关系 → 01 书封 → 02 文案 → 03 内容审核 → 04 配音 → 05 分镜 → 06 素材 → 07 渲染 → 08 交付 → 09 规格写作 |
| `accounts/` | 账号人设 + `visual_style_profile` 五层；字幕样式由 `assemble.py` 读取 |
| `config/` | `theme-presets`（8 套色板）/ `grammar-presets`（语法白名单与选型树）/ `ebook-sources` |
| `samples/t21-30s/` | **T21 30 秒样例**：成片、plan、manifest、lint 结论 |
| `assets/fonts/` | NotoSansSC ×4 + NotoSerifSC（引文实际用 vendor 的 `LXGWWenKai-500`） |

## 从 GitHub 安装 / 更新

```bash
git clone --depth 1 https://github.com/buikiet8080g-lab/booklist-pipeline-htmlmotion.git \
  ~/.pi/agent/skills/booklist-pipeline-htmlmotion
```

也可以直接在 GitHub 页面 **Code → Download ZIP**，解压后放到 `~/.pi/agent/skills/booklist-pipeline-htmlmotion`。

- 本仓库的 `vendor/huashu-art-motion/` 是**去掉嵌套 `.git` 的完整源码副本**（144M → 92M），开箱即可渲染，无需联网拉上游。
- 因此 `ours/env_check.py` 会把「vendor 无 .git」列为降级提示（⚠），不算失败；需要严格校验 tag/改动时按 `vendor/BASELINE.md`「离线副本」重新 `git init`。

## vendor 基线

| 项 | 值 |
|---|---|
| 上游 | https://github.com/alchaincyf/huashu-art-motion （MIT） |
| tag / commit | `v1.2.0` / `8f0a349` |
| 体积 | 仓库 144M；`scripts/engine` **24M**（字体 16M） |
| 获取（在线） | `git clone --depth 1 --branch v1.2.0 <url> vendor/huashu-art-motion` |
| 获取（离线） | `cp -R ~/.pi/agent/skills/huashu-art-motion vendor/huashu-art-motion` + `git init && git add -A && git commit && git tag v1.2.0`（详见 BASELINE.md） |
| 只读 | 是。所有改动只在 `patches/` |

## 补丁清单

| # | 文件 | 修什么 |
|---|---|---|
| 0001 | `y2_vox.js` | 竖屏桌面链垂直居中；冲印件高按内容带约束；`data.tape:false` |
| 0002 | `t2_keynote_ui.js` | 竖屏卡片高度上限 400u→560u，死区 35%→<10% |
| 0003 | `y3_whiteboard.js` | 竖屏内容垂直居中、文字栏加宽、字号系数上限 1.6 |
| 0004 | `bl_quote.js`（新） | 书中原文引文语法（文楷、引号、跨行荧光笔、出处两段式） |
| 0005 | `bl_cover_hero.js`（新） | 书封主打语法（书封占主体、整张不裁、角标、呼吸推进） |
| 0006 | `clip.js` + 8 语法 | cue 白名单：非法 kind 由静默丢弃改为启动失败 |

## 升级流程

```bash
cd vendor/huashu-art-motion && git fetch --tags && git checkout v1.3.0
cd ../.. && ./patches/apply.sh          # 冲突手工并，然后重新导出对应 patch
python3 ours/env_check.py               # tag / 体积 / 补丁状态
cd samples/t21-30s && python3 ../../ours/lint_spec.py metadata/plan.json   # 回归
```

## 已知边界

- 只做竖屏 720×1280、只做 `script_mode=clean`；`original`（原创选题）未实现。
- y3 中段留白 30–40%（optional）；y2 竖屏只做图片主导；t3 来源行 21px。
- 样例封面是排版占位图（造 Skill 环境无网络），生产必须换成 01 核验的真实封面。
