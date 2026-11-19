# 09 规格写作指南（5 个语法的 cue 正反例）

模型在 05 只做一件事：**往 `plan.json` 的 `shots[].spec.cues[]` 里填 cue**。一镜 1–4 条，每条 `{at, kind, text?, sub?, data?, image?}`。
`at` 是「这一条第一次可见」的秒数（相对本镜开头）。写错 `kind` 现在会启动失败（`patches/0006`）。
**滑到最后一节看「七个最常见的写错」。**

---

## 1. `bl_cover_hero` — 书封主打 / CTA

允许的 kind：`cover`（必须 1 条）、`text`（可选，控制那句副标题的落定时刻）。

```jsonc
// 正例：书籍导入（每片第一镜常用）
"spec": { "cues": [
  { "at": 0.06, "kind": "cover", "image": "images/cover-verified.jpg",
    "text": "被讨厌的勇气", "sub": "岸见一郎 / 古贺史健",
    "data": { "tag": "豆瓣 8.6", "press": "机械工业出版社" } }
]}
```

| 反例 | 会发生什么 | 正确写法 |
|---|---|---|
| `{"kind":"cover"}` 不写 `image` | 启动失败：`cover cue 没有可用的 book_cover 图片` | 必须给 `image`，且是 01 核验过的封面 |
| `image` 写 `"cover.jpg"`（相对项目根） | 路径按 spec 文件解析 → 找不到 → 拒渲 | `render_batch.py` 会自动改成绝对路径；手写 spec 时写相对项目根 |
| `text` 写 20 字书名+副标题 | 会折两行、字号自动缩到放得下；超过 2 行就挤 | 书名 ≤14 字；副标题放 `sub` |
| `data.tag` 写 12 字 | 角标会被 `TY.fit` 缩到很小、压在封面右上 | 角标 ≤8 字（「豆瓣 8.6」「销量 1000 万」） |
| 同一个 spec 里 `image` 换成模型生成的封面 | `lint_spec` 红灯（E09） | 回 01 换真实封面 |

CTA 用法：末尾一镜用同一语法，`data.tag` 写动作（「想读的点开」），`sub` 写路径（「橱窗在左下角」）。

---

## 2. `bl_quote` — 书中原文引文

允许的 kind：`quote`（必须 1 条）、`source`（可选，出处落定时刻）。

```jsonc
// 正例：引文镜（8–12s，观众要读完）
"spec": { "cues": [
  { "at": 0.06, "kind": "quote", "text": "把孩子的课题还给孩子",
    "data": { "source": "《被讨厌的勇气》", "author": "岸见一郎 / 古贺史健",
              "page": "第 88 页", "key": "课题" } }
]}
```

| 反例 | 会发生什么 | 正确写法 |
|---|---|---|
| 引文写 80 字 | 字号一路缩到 40px 以下（读不动）；`lint` 报黄 | 引文 ≤60 字、≤6 行；长段改转述，不要整段贴 |
| `data.key` 写整句 | 荧光笔会划一大条，压掉半个画面 | 关键词 2–6 字 |
| `data.key` 跨行（「不可爱」被折成「不可」/「爱」） | 会自动按每行最长片段划（≥2 字），能划出来但不是整词 | 想整词高亮就把关键词放在不会断的位置，或接受分段划 |
| `text` 里带书名号 | 出处行会重复书名 | 书名放 `data.source`，正文只放原文 |
| 不写 `data.source` / `page` | 出处行只有作者，可信度下降（书单号的核心是「这是书里的原话」） | `source` 必写；页码查不到就留空，别编 |

---

## 3. `y5_kinetic_type` — 要点 / 清单 / 金句 / 数字

允许的 kind：`title`、`point`、`number`、`highlight`。

```jsonc
// 正例 A：清单（竖屏主力，≥2 页才有进度轨 + 背景序号，下半屏不空）
"spec": { "cues": [
  { "at": 0.06, "kind": "point", "text": "先看见情绪", "sub": "说出他的感受" },
  { "at": 1.86, "kind": "point", "text": "再说明规则", "sub": "一次只说一条" },
  { "at": 3.66, "kind": "point", "text": "最后给选择", "sub": "两个都行，你选" },
  { "at": 4.60, "kind": "highlight", "data": { "word": "最后给选择" } }
]}

// 正例 B：一个大数字（data.value 是落定值，at = 落定时刻）
{ "at": 0.9, "kind": "number", "text": "翻了两倍半", "data": { "value": 2.5, "suffix": " 倍", "decimals": 1 } }
```

| 反例 | 会发生什么 | 正确写法 |
|---|---|---|
| 只写 1 条 `point`（单页） | 内容带下半屏空 30%+，`lint` 报黄 | 竖屏写 ≥2 页；单句金句改用 `bl_quote` |
| `{"kind":"quote","text":"..."}` | **整页静默消失**（打 0006 前）；现在启动失败 | y5 没有 quote 原语，引文用 `bl_quote` |
| `data.label`（左上小标签） | 竖屏里标签压在巨型主词上（实测「02」压住「再」） | 竖屏不写 `data.label`；序号用进度轨表达 |
| 主词 12 字以上 | 自动折 2 行、字号被压到很小 | 主词 ≤8 字；整句放 `sub` 或字幕 |
| `highlight` 的 `word` 不在主词里 | 只告警、什么都不发生 | `word` 必须是主词里的原样子串 |
| 一镜里塞 5 页 | 每页不到 1.5s，读不完 | 一镜 2–3 页；更多内容拆镜 |

---

## 4. `t3_finance_chart` — 数据 / 对比 / 趋势

允许的 kind：`title`、`bar`、`line`、`candle`、`highlight`、`number`。
数据写在 `spec.data`（`series` + `highlight`），cue 只控制「什么时候长出来 / 什么时候标注」。

```jsonc
"spec": {
  "data": { "title": "孩子每天被否定的次数", "unit": "次/天，父母自报（2020–2024）",
            "source": "来源：《正面管教》第 3 章 + 家长自报样本",
            "chart": "bar", "decimals": 0,
            "series": [ {"label":"2020","value":18}, {"label":"2022","value":31}, {"label":"2024","value":45} ],
            "highlight": { "index": 2, "text": "2.5 倍", "sub": "45 ÷ 18" } },
  "cues": [ { "at": 0.4, "kind": "bar", "data": { "index": [0,1,2] } },
            { "at": 3.1, "kind": "highlight" } ]
}
```

| 反例 | 会发生什么 | 正确写法 |
|---|---|---|
| `"index": "all"` | 不报错，但**一根柱子都不长** | `"index": [0,1,2]`（序号或序号数组） |
| 没写 `data.series` | `lint` 红灯 E17 | 数据必须来自真实来源；没有数据就用 y5 说结论 |
| 没写 `data.source` | `lint` 报黄 W13 | 数据镜必须能溯源（书单号最容易被质疑的地方） |
| 编一个「3 倍」但数据是 2.5 倍 | 03 阶段就该拦；`lint` 查不出 | 屏上数字必须能在文案/原书里查到（§14.2 ①） |
| 一镜 8 根柱子 | 标签挤在一起、字号被压 | ≤6 根；多了拆镜或改成 `line` |
| 和前后镜不同色板 | 画面像贴了一张别的片的图 | `theme` 全片一套（`wood` 的图表底也是 `wood`） |

**已知**：来源行是 21px 的小字（角标级信息），不计入「正文 ≥32px」；位置在 `H−300` 上方，不会压字幕。

---

## 5. `y2_vox` — 真实素材满幅 + 标注

允许的 kind：`image`/`clip`（素材）、`title`、`point`、`highlight`（`data.rect`）。
**竖屏铁律：只做图片主导。** 文字卡改用 y5。

```jsonc
"spec": { "cues": [
  { "at": 0.2, "kind": "image", "image": "images/003-desk.jpg", "text": "真实的书桌",
    "data": { "tape": false } },
  { "at": 3.0, "kind": "highlight", "data": { "rect": [0.18, 0.34, 0.52, 0.18] } }
]}
```

| 反例 | 会发生什么 | 正确写法 |
|---|---|---|
| 一镜里 1 张图 + 3 张文字卡 | 文字卡横宽矮，竖屏下半屏必然空（实测死区 45%） | 图 + 0–1 张卡；文字内容用 y5 另起一镜 |
| `data.rect` 写像素 `[120,300,200,90]` | 会被当成 0..1 的比例（画到画面外） | 归一化 0–1，相对图片 |
| `highlight` 在图片 cue 之前 | 那一镜没有图可圈，什么都不发生 | `highlight.at` 必须晚于对应 `image.at` |
| 用代码画「假装照片」的图形替代 | 违反反模式 #9，一眼假 | 没有素材就不做 y2 镜 |
| `data.tape` 不写 | 有胶带（默认），逐帧多画两片半透明纸 | 竖屏精简模式写 `"tape": false` |

---

## 6. 可选语法（y3 / t2）速记

- `y3_whiteboard`：`title` / `point` / `draw`（`data.icon`：clock target bulb …）/ `image` / `highlight`。**每片 ≤1 镜、≥4 条要点**，否则中段留白 30–40%。
- `t2_keynote_ui`：`title` / `card` / `step` / `image` / `highlight` / `number`。竖屏 1–3 张卡一屏；有截图时自动满幅 + 推近。

---

## 7. 七个最常见的写错（每条都真实踩过）

1. **cue 写错 kind** → 原来静默丢页，现在启动失败。对照 ✓/✗ 表：`quote` 只属 `bl_quote`，`cover` 只属 `bl_cover_hero`。
2. **字号用 `*u` 混屏幕 px**：`u = min(W,H)/1080 = 0.667`，`40*u` 只有 27px，低于 32px 下限。正文写屏幕 px。
3. **引文用 `NotoSerifSC`** → 字库是示范片子集（缺「孩爱候他」），回退黑体。用 `LXGWWenKai-500`（bl_quote 已内置）。
4. **给 y5 写 `data.label`** → 竖屏压住主词。
5. **t3 写 `"index":"all"`** → 柱子不长，还不报错。
6. **字幕写进场景**（把整句塞进 `text`）→ 屏上字超过 12 汉字、字号被压、还和后期字幕打架。屏上字是关键词，整句归字幕。
7. **同片中途换 `theme`** / `data.palette` 整覆盖 → 画风漂移、序号不可见。色板全片一套，只允许改 accent 单键。

## 8. 自查顺序

```bash
python3 <skill>/ours/lint_spec.py metadata/plan.json --static-only   # 规格规则（秒级）
python3 <skill>/ours/lint_spec.py metadata/plan.json                 # 加动态抽帧（边缘/截断/叠字/空帧）
python3 <skill>/ours/render_batch.py metadata/plan.json --workspace . --only <改过的镜>
```
