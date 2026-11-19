# 归属与许可

本 Skill 的渲染层来自上游开源项目：

- **huashu-art-motion** — https://github.com/alchaincyf/huashu-art-motion
- 许可：MIT（全文见 `vendor/huashu-art-motion/LICENSE`）
- 基线：tag `v1.2.0`，commit `8f0a349`
- 使用方式：`vendor/huashu-art-motion/` 为**原样只读副本**，未做任何字节级修改。

我们对上游的全部改动以 patch 形式存放，共 6 个（见 `patches/README.md`）：

| patch | 类型 | 影响的文件 |
|---|---|---|
| 0001–0003 | 竖屏适配 | `clips/y2_vox.js`、`clips/t2_keynote_ui.js`、`clips/y3_whiteboard.js` |
| 0004–0005 | 新增语法（booklist 专用，前缀 `bl_`） | `clips/bl_quote.js`、`clips/bl_cover_hero.js` |
| 0006 | cue 白名单校验 | `clip.js` + 8 个 `clips/*.js` |

字体：`assets/fonts/` 中的 NotoSansSC / NotoSerifSC 来自上游 `lib/fonts/`（OFL 1.1，见 `vendor/huashu-art-motion/scripts/engine/lib/fonts/OFL.txt`）。
引文使用的 `LXGWWenKai-500`（霞鹜文楷）同为 OFL 1.1，随上游附带。

本 Skill 自身的编排层（`ours/`、`references/`、`SKILL.md`）由本项目编写。
