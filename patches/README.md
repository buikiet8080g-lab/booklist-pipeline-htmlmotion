# patches · vendor 的唯一改动位置

`vendor/huashu-art-motion/` 是上游 **v1.2.0**（commit `8f0a349`）的只读副本，**一个字节不许改**。
我们对上游的全部改动都在这 6 个 patch 里，**顺序 apply、可重放、可回滚**。

```bash
./patches/apply.sh                      # 从干净 vendor 开始，顺序 apply（fail-fast）
cd vendor/huashu-art-motion && git status --porcelain   # 应只列出下面这些文件
git checkout -- . && rm -f scripts/engine/clips/bl_{quote,cover_hero}.js   # 回到干净基线
```

| # | 文件 | 修什么 | 验证 |
|---|---|---|---|
| 0001 | `clips/y2_vox.js` | ① 竖屏整条桌面链在内容带 `[safe.top, H−safe.bottom]` 里垂直居中（2 件时下方死区 45%→0）② 冲印件高度按 `Hs−12u` 约束，整张含白边不越出内容带（原来会贴到画布顶边）③ `data.tape:false` 关胶带（竖屏精简模式） | `y2` 8s 竖屏抽帧：无溢出、无截断，图片主导时死区 <20% |
| 0002 | `clips/t2_keynote_ui.js` | 竖屏卡片高度上限 400u→560u，按可用高度算：两张卡从 578px 撑到 775px，第三方下方死区 35%→<10% | `t2` 3 卡竖屏抽帧：卡片不出安全区、内容带利用 >80% |
| 0003 | `clips/y3_whiteboard.js` | ① 内容整块在内容带里垂直居中（原来固定从 `safe.top+240u` 往下写，中段死区 51%）② 图标栏 250u→200u、间距 70u→40u，把宽度让给文字栏（9 字句不再折成两行）③ 字号系数上限横屏 1.2 / 竖屏 1.6 | `y3` 竖屏抽帧：不溢出、不截断；中段留白 30–40%（白板本身留白，已写进诚实边界） |
| 0004 | `clips/bl_quote.js`（新增） | **新语法**：书中原文引文。大引号砸入 → 正文逐行升起 → 关键词荧光笔（跨行也能划）→ 出处两段式落定。字号 88→40px 自适应（按宽高取最大能放 6 行的一档），左安全边 56px，出处 34/32px 屏幕字号（不低于 32px 下限） | 8s 竖屏抽帧：引文不出界、不改字号到 <40px、出处不拆词、不贴边 |
| 0005 | `clips/bl_cover_hero.js`（新增） | **新语法**：书封主打。书封高 = 内容带 80%（竖屏 720px，宽 ≥55%），整张 contain 绝不裁；书脊压边 + 投影让它立起来；一句话 + 作者/出版社两段；可选角标；全程 1.5% 呼吸推进 | 8s 竖屏抽帧：书封占比 ≥55%、不缺图（缺图直接启动失败）、书名不截断 |
| 0006 | `clip.js` + 8 个语法文件 | **cue 白名单**：每个语法声明 `kinds:[...]`，`clip.js` 启动时校验，未知 kind 直接 `fail()`。原来写错 kind 会被静默丢弃（给 y5 写 `quote`，整页消失、`--audit` 还报 0 红灯） | 给 y5 写 `kind:"quote"` → 启动失败、`render.py` 非零退出、`lint_spec` 红灯（T13） |

## 两条纪律

1. **一个 patch 只做一件事**。改动跨文件时（0006），先 `git apply` 前面的 patch 再生成 diff，否则会把别的 patch 的内容卷进来。
2. **验证失败只修那一个 patch**：改 vendor 工作树 → `git diff -- <该文件> > patches/000N-*.patch` → 回滚 → 从干净 vendor 重放全部 6 个 → 抽帧复验。不要「顺手」改别的文件。

## 升级上游（Q7：跟随）

```bash
cd vendor/huashu-art-motion && git fetch --tags && git checkout v1.3.0
cd ../.. && ./patches/apply.sh        # 冲突就手工并，改完重新导出对应 patch
python3 ours/env_check.py             # 基线 tag / 体积 / 补丁状态自检
```

patch 数硬上限 6 个。要加新补丁，先合并或删除旧的 —— 超过 6 个说明改动方向错了（应该改成 `ours/` 里的编排，而不是改 vendor）。

## 已知取舍

- `0003` 的 y3 竖屏仍有 30–40% 中段留白：白板语法天生「写到哪算哪」，内容少就空。**用法约束**：y3 每片 ≤1 镜、至少 4 条要点（写进 `references/09`）。
- `0001` 没让 y2 的文字卡填满竖屏：一张横宽卡片在 720×1280 里无法既不满宽又不空下半屏。**用法约束**：y2 竖屏只做图片主导（写进 `references/09` + `lint_spec` 的 y2 检查项）。
- `0006` 的 `kinds` 表要跟语法实现同步维护；新增语法时记得在文件里声明 `kinds`。
