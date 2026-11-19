# 04 MiMo 主音轨（分块并发 → 顺序拼接）

主音轨是**全片时间的尺子**：05 按它的时长切镜，08 按它对齐成片。所以 04 的时长必须实测入档。

## 最快路径：`ours/tts_mimo.py`（一条命令，自动分块并发拼接）

```bash
python3 <skill>/ours/tts_mimo.py --script 02-final-script.md \
  --account <skill>/accounts/family-education-parent-reader.md \
  --out audio/main-voice.wav
```

- 自动按 180–350 字切段（句末/段末优先），3 路并发调 MiMo，顺序拼成 `main-voice.wav`；
- 音色与 `program_name` 从账号 md 读，声音导演用内置默认（可用 `--style-file` 覆盖）；
- 没有 `MIMO_API_KEY` **直接报错**，不静默降级成机器音；
- 产出 `metadata/04-voice/04-audio.json`（每段耗时/时长/文本）+ `04-audio.md`。

`ours/run_all.py` 在没有 `audio/main-voice.wav` 时会自动先跑这一步。

## 手动调（要精细控制某一段时）

```bash
python3 <skill>/mimo-tts-generator/scripts/generate_mimo_tts.py \
  --style-file metadata/04-voice/001-user.txt \
  --text-file  metadata/04-voice/001-assistant.txt \
  --voice 茉莉 --audio-format wav --segment-id 001-main \
  --program-name <账号 program_name> \
  --download-to audio/chunks/001-main.wav \
  --output metadata/04-voice/001-main.json
```

- `user.content` 只写**声音导演**（角色/场景/指导/禁用腔调/情绪弧线），不会进音频。
- `assistant.content` 才是要合成的话，**一字不改**（改文案回 02，不在 04 顺手改）。
- 单段 180–350 汉字；语义节拍处切（痛点 / 读后发现 / 价值揭示 / 现实收益 / CTA）。3–4 段并发，再按顺序拼。
- 音色按账号：家庭教育 = `茉莉`；传统文化 = `白桦`（见 `accounts/`）。

## 拼接与验收

```bash
ffmpeg -y -v error -f concat -safe 0 -i audio/concat.txt -c:a pcm_s16le audio/main-voice.wav
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 audio/main-voice.wav
```

| 检查 | 判据 |
|---|---|
| 首尾完整 | 第一句是全文第一句、最后一句是 CTA，没有被截断的字 |
| 段间空隙 | 相邻 chunk 的接缝处不吞字、不重复（听 2 个接缝即可） |
| 时长入档 | 写进 `04-audio.md` 与 `metadata/04-voice/*.json` 的 `duration_seconds` |
| 音量 | 全片整体 -16 LUFS 左右（08 混音时统一，不在这里压） |

## 输出

```
audio/main-voice.wav        # 全片唯一主音轨（08 用它）
audio/chunks/*.wav          # 分段留档（重跑单段用）
metadata/04-voice/*.json    # 每段的 program_name / segment_id / voice / style / duration
04-audio.md                 # 人读：分段策略、实测时长、试听结论
```

## 闸门

- `main-voice.wav` 时长实测 > 10s 且 < 900s。
- 没有漏尾 / 漏 CTA。
- 时长写进 `04-audio.md`，05 会用 `ffprobe` 再核一次。
