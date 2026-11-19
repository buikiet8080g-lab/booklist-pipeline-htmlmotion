# 05 分镜计划（★核心）：文案 → 镜头

**05 的唯一工作是把文案切成「一个画面事件 = 一镜」，再给每镜挑一个白名单语法。** 输出的 `plan.json` 是 07 的唯一输入。

## 一镜是什么

一镜 = 观众在这一刻该看懂的一件事。判据：能写出「**物 + 动词**」（书封+升起 / 柱子+长出来 / 引文+逐行写出）。
写不出物和动词 → 这一镜不该存在，并到上一镜或拆下一镜。

## 秒数

| 内容 | 秒 |
|---|---|
| 常规叙述 | 6–8 |
| 引文（要读完） | 7–12 |
| 数据 / 时间线 / 多步对比 | 10–15 |
| CTA | 5–8 |
| 标题 / 单句强调 | 2–3（只作为镜头内部阶段，不单独成镜） |

超过 15 秒必须拆；一镜里出现「第二次新信息」就拆。

## 配比（`shot_plan.py` 自动兜，`lint_spec.py` 复核）

- 文字主导镜头（y5 / t3）≤ 全片 30%。
- 每 3 镜至少 1 镜真实素材（书封 / 实拍）。
- 不许连续 3 镜同语法。
- 首镜不许是纯标题卡（必须是具体画面事件：书封升起也算）。
- 尾镜不许是纯金句卡；CTA 必须带书封。
- 推进型入场（每镜推近）全片 ≤40%，相邻两镜换构图不换画风。

## 自动模式的三个护栏

1. **书名自动识别**：`--book auto` 从文案里第一个《…》取书名；作者/出版社可缺。书封必须由 `--cover` 显式给一个真实文件（缺 → 阻塞，D16）。
2. **镜数自适应**：每镜至少 5.5s；句子比可用镜数多时合并相邻句（优先不合并含引文的），不产出 4s 碎镜。
3. **文案与音轨同源校验**：按 3–5 字/秒检查，偏差过大直接报错（说明拿错了音轨或漏了段落），不拖到成片才发现。
4. **短片的镜数**：整片 <25s 时镜头下限放到 4.5s（`lint` 红线同口径），否则 4 句文案会被迫并成 3 镜、丢掉中间内容。
5. **y5 自动拆点**：「……三件事：先看见情绪，再说明规则，最后给他选择」会自动拆成 3 页清单（带进度轨），避免单页把竖屏下半屏留空。

## 怎么跑

```bash
# 自动切镜（音轨时长按句子权重分配，再按语法要求重排、对齐总时长）
python3 <skill>/ours/shot_plan.py --script 02-final-script.md --audio audio/main-voice.wav \
  --book metadata/book-assets.json --theme wood --account family-education-parent-reader \
  --out metadata/plan.json --markdown 05-shot-plan.md

# 覆盖：sheet.json 按顺序对齐镜头（不写 grammar 就自动选）
python3 <skill>/ours/shot_plan.py ... --sheet metadata/sheet.json
```

`sheet.json` 每项可写：`grammar` / `text` / `sub` / `points[]`（y5 清单）/ `series`+`highlight`（t3）/ `image`+`rect`（y2）/ `key`+`page`（bl_quote）/ `tag`（CTA）。

## plan.json 的 shot 字段

```jsonc
{
  "id": "006-1", "start": 41.2, "duration": 7.4,
  "scene_type": "kit",                       // kit | free（free ≤10%，必须写 free_scene_reason）
  "grammar": "bl_cover_hero",                // 见 grammar-presets.md 白名单
  "theme": "wood",                           // 同片一套
  "safe": {"top": 80, "bottom": 300},
  "spec": { "cues": [ ... ] },               // 直接透传给语法，不做二次包装
  "narration_span": [41.2, 48.6],
  "subtitle_lines": ["这本书我读了两遍"],
  "book_cover_required": true,
  "assets": [{"role": "book_cover", "path": "images/cover-verified.jpg"}],
  "heavy_accent": false
}
```

## 闸门

```bash
python3 <skill>/ours/lint_spec.py metadata/plan.json            # 静态 + 动态抽帧
python3 <skill>/ours/lint_spec.py metadata/plan.json --static-only   # 秒级，改文案时先跑这个
```

红灯项：非法 grammar / 非法 cue kind / 镜长越界 / 总时长与音轨差 >0.3s / 书封缺失 / free_scene 超比 / 蓝紫色 / 文字贴画布边 / 文字落进字幕区 / 文本被截断 / 空帧。

## 返工路由

| 现象 | 改哪 |
|---|---|
| 文字出界 / 压字幕 / 截断 | 改该镜的 `plan.json` 条目（`--only <id>` 重渲，不重渲全片） |
| 节奏拖 / 该说的没到位 | 改 05 的分镜边界（拆镜或挪文案），重渲受影响镜 |
| 书封不对 | 回 01 换资产，重渲引用该资产的镜 |
| 字幕不同步 | 只重跑 08，不动画面 |
