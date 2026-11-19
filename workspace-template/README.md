# 项目目录模板

```
<项目>/
├── 01-book-assets.md            # 01：核验过程
├── 02-final-script.md           # 02：纯正文（TTS 直接读）
├── 02-rewrite-record.md
├── 03-script-audit.md
├── 04-audio.md
├── 05-shot-plan.md              # 05：shot_plan.py 生成
├── 06-image-assets.md
├── 08-final-delivery.md         # 08：assemble.py 生成
├── images/cover-verified.jpg    # 01：全片唯一真实书封
├── audio/main-voice.wav         # 04
├── metadata/
│   ├── book-assets.json         # 01
│   ├── sheet.json               # 05：可选，按顺序覆盖每镜
│   ├── plan.json                # 05：下游唯一输入
│   ├── specs/<id>.json          # 07：实际送进 render.py 的 spec
│   ├── render-manifest.json     # 07
│   ├── subtitles.ass            # 08
│   └── 04-voice/*.json          # 04
├── clips/<id>.mp4               # 07
├── render/master-noaudio.mp4    # 07
└── final/发布版-*.mp4           # 08
```

## sheet.json 示例

```json
[
  {"grammar": "bl_cover_hero", "text": "被讨厌的勇气", "sub": "岸见一郎 / 古贺史健"},
  {"grammar": "bl_quote", "text": "把孩子的课题还给孩子", "page": "第 88 页", "key": "课题"},
  {"grammar": "y5_kinetic_type", "points": [
     {"text": "先看见情绪", "sub": "说出他的感受"},
     {"text": "再说明规则", "sub": "一次只说一条"},
     {"text": "最后给选择", "sub": "两个都行，你选"}]},
  {"grammar": "bl_cover_hero", "text": "被讨厌的勇气", "sub": "橱窗在左下角", "tag": "想读的点开"}
]
```

## captions.json 示例（08 用）

```json
[{"start": 0.0, "end": 2.6, "text": "很多父母以为，不吼孩子靠的是忍住。"},
 {"start": 2.6, "end": 6.2, "text": "这本书里说：把孩子的课题还给孩子。"}]
```
