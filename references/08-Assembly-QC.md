# 08 收尾：混音 + ASS 字幕 + QC + 交付

## 顺序

1. `render/master-noaudio.mp4`（07 的产物）+ `audio/main-voice.wav`（04 的产物）
2. 字幕：**默认自动对齐**——`ours/align_subtitles.py` 用 `ffmpeg silencedetect` 找语音停顿，把 02 的句子按字数落到每个说话段上（不需要 key、不需要参数；`run_all` 自动跑）。
   有 ASR（GROQ / 本地 whisper）时可以用它产出的 `captions.json` 覆盖，`--captions` 直接喂给 `assemble.py`。
3. 生成 ASS → ffmpeg 烧录 → `final/发布版-*.mp4`
4. ffprobe QC → 写 `08-final-delivery.md`

```bash
python3 <skill>/ours/assemble.py metadata/plan.json --workspace . \
  --video render/master-noaudio.mp4 --audio audio/main-voice.wav \
  --captions metadata/captions.json \
  --account <skill>/accounts/family-education-parent-reader.md
```

## 字幕铁律（D15）

- **绝不写进场景代码**：改一个错字要重渲全片是设计事故。
- 底部 300px 安全区：`MarginV=110` + `fontsize=46` → 字幕落在 1000–1230，正文区 `y<980` 不被侵占。
- 一条字幕最多 3 行、每行 ≤12 汉字；超长在标点断，没标点硬断（`assemble.py` 的 `wrap_sub`）。
- 对齐判据：每句字幕落在对应说话段上、`4±0.5 字/秒`、不重叠、首尾不出音轨；`metadata/subtitle-align.json` 留证。
- 字体用系统 `WenQuanYi Zen Hei`（**woff 不能给 libass**）。
- 描边 3px，不发光、不加阴影（书单号受众偏大，清晰优先）。

## QC 表（`assemble.py` 自动跑）

| 项 | 判据 |
|---|---|
| 分辨率 | 720×1280 |
| 帧率 | 24 |
| 有音轨 | AAC，时长与音轨差 ≤0.5s |
| 字幕位置 | `MarginV + size*1.35 ≤ 360`（不进正文区） |
| final/ 唯一 | 顶层只有一个 mp4 |

再人工过一遍（30 秒）：

- 前 3 秒有具体画面事件（不是标题卡）。
- 每 3 镜至少一次真实书封。
- 相邻两镜构图不同、画风一致（同一个 `theme`）。
- 字幕与口播同步，没有一条字幕溢出画面。
- 结尾 CTA 有书封 + 可执行动作。

## 发布信息包

`08-final-delivery.md` 里写：成片路径、时长、封面（01 的封面）、标题 3 个候选、正文钩子、话题标签、CTA 话术。
不要写「本片由 AI 生成」这类与内容无关的描述；平台要求的 AI 声明另开一节。

## 输出

```
final/发布版-<account>-<theme>.mp4
metadata/subtitles.ass
08-final-delivery.md
```
