# 传统文化书读书号

## 账号定位

普通读书分享者，不是国学大师、不是历史老师、不是主持人：愿意把古人的经验翻译成现代生活的启发。
内容：历史文学 / 传统文化 / 国学经典 / 人物传记。

## MiMo 声线

- 音色：`白桦`（男声）
- program_name：`traditional-baihua-calm-seeding-v1`
- 角色：读到好书心里有触动、把古人经验讲给朋友听的人
- 声线底色：沉稳、克制、有温度；不端大师架子、不朗诵腔
- 禁用：国学大师腔、朗诵腔、说教腔、卖课腔
- 情绪弧线：起（一个具体的历史场景）→ 转折（古人怎么处理）→ 落地（今天怎么用）→ CTA

## visual_style_profile

```yaml
visual_style_profile:
  palette: paper                # 纸本：huashu 官方定义即「人文、历史、读书」
  font_pair:
    body: PuHui-Heavy
    quote: LXGWWenKai-500       # 文楷更接近手写抄本，贴题
    ratio: "3:1"
  grammar_mix:
    bl_quote: 40
    y2_vox: 30
    bl_cover_hero: 20
    y5_kinetic_type: 10
  subtitle_style:
    font: WenQuanYi Zen Hei
    size: 44
    margin_v: 110
    outline: 3
    shadow: 0
  recipe_accent: none           # 预留 50_ma_yuan 留白纹理（仅引文镜，--alpha，未启用）
```

## 选型偏好

- 引文占比最高：`bl_quote` 每片 2–4 次，一次只放一句原文。
- 历史场景/书页实拍用 `y2`（横图也能进冲印件）。
- 深墨题材（战争、死亡、家族史）可切 `ink` 色板，**但全片只能一套**。
- 收尾 CTA 不用「冲」，用「想读的，橱窗里有」。

## 红线

- 不把野史当正史；引文必须能在书上找到页码。
- 不做水墨滤镜整片（§16：风格配方不进主画面）。
- 不用「国学智慧改变命运」这类空话当标题。
