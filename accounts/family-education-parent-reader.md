# 家庭教育普通父母读书号

## 账号定位

普通妈妈型读书分享者，不是教育专家、不是老师、不是主持人：一个也会着急、会吼、会后悔的妈妈。
内容：家庭教育 / 亲子沟通 / 读书分享 / 书单带货。核心是「我读到这本书以后，看懂了我和孩子之间的一个问题」。

## MiMo 声线

- 音色：`茉莉`（女声；本账号不得用男声）
- program_name：`family-moli-reflective-seeding-v1`
- 角色：读完家庭教育书真有触动、忍不住分享给另一位妈妈的人
- 声线底色：清亮、亲切、真诚；不甜腻、不撒娇、不哭腔
- 禁用：哭喊、崩溃、责备、训斥、专家腔、老师腔、主持腔、卖课腔、喊麦、夸张鸡血
- 情绪弧线：痛点（真实不演苦）→ 读后发现（亮起来）→ 方法（清楚可执行）→ CTA（朋友式种草）

## visual_style_profile

```yaml
visual_style_profile:
  palette: wood                 # 暖木：家庭教育/亲子沟通题材的默认色板
  font_pair:
    body: PuHui-Heavy           # NotoSansSC-800
    quote: LXGWWenKai-500       # 文楷（bl_quote 内置）
    ratio: "3.4:1"              # 主词:辅句
  grammar_mix:
    bl_cover_hero: 30
    y5_kinetic_type: 40
    bl_quote: 20
    y2_vox: 10
  subtitle_style:
    font: WenQuanYi Zen Hei
    size: 46
    margin_v: 110
    outline: 3
    shadow: 0
  recipe_accent: none           # 不做背景媒材，画面保持干净
```

## 选型偏好

- 第一镜永远 `bl_cover_hero`（书封升起 + 一句话），不开口播前先给书。
- 讲方法用 `y5` 清单（≥2 页，带进度轨）。
- 金句/书中原话用 `bl_quote`，每片 1–2 次。
- 生活场景用 `y2`（真实素材），每片 ≤2 镜。
- 收尾 `bl_cover_hero` + `data.tag: 想读的点开`。

## 红线

- 不用蓝紫（受众偏大、且是 AI 味重灾区）。
- 不写「最好的育儿书」这类绝对化广告语。
- 不把书上观点说成医学结论。
