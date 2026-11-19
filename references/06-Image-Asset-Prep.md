# 06 图片素材（默认 none；书封永远来自 01）

**默认 `image_need=none`（D18）**：书单号 80% 的画面是书封、引文、要点、数据，都由语法库画出来，不需要出图。
只有下面两种镜头才请求出图：`y2_vox`（实拍/生活场景，要真实素材）与需要辅助书的 `bl_cover_hero`。

## 什么时候要图

| 镜头内容 | 要不要图 | 怎么来 |
|---|---|---|
| 书名/推荐/适合人群/CTA/核心概念首现 | 不要图，要**书封** | 01 的 `images/cover-verified.jpg` |
| 书中案例 / 生活场景（y2） | 要 | `apimart-image-generator` 出图，或已核验实拍 |
| 结构/步骤/对比/因果/数据 | 不要 | 语法库代码画（y5 / t3） |
| 情绪/氛围 | 最多 1–3 镜，不连续 3 镜 | 出图或压暗实拍 |
| 需要出现人 | 只出手、背影、局部 | 出图时在 prompt 里写明 |

## 出图（`apimart-image-generator`）

```bash
python3 <skill>/apimart-image-generator/scripts/generate_image.py --prompt "<场景>" --size 720x1280 --out images/003-scene.jpg
```

- **书封作为 `reference_images` 传入**，不是让模型凭书名画封面（D16）。
- 竖屏素材直接出 720×1280 或 4:5；横图会被 y2 的冲印件加白边，可接受。
- 九宫格批量（3×3）仍保留：`python3 <skill>/ours/crop_grid_image.py --input grid.png --out-dir images/ --cell-aspect 9:16`。

## 闸门

```bash
python3 <skill>/ours/image_provider_policy.py --state metadata/image-provider.json   # provider 优先序与最近成功
python3 <skill>/ours/audit_book_cover_policy.py metadata                            # 书封政策
```

- 书封槽位图必须与 01 的 `sha256` 一致（`lint_spec.py` 校验文件存在；渲染 manifest 记录 sha）。
- 不许在图片阶段给书封做贴图/合成修补（继承 Lite `source_image_book_cover_composite_forbidden`）。
- 出图失败不降级成「代码画假装照片」（反模式 #9）：换素材或换语法。

## 输出

```
images/*.jpg            # 本片用到的全部素材
06-image-assets.md      # 每张：用途、镜头 id、来源、prompt、sha256
metadata/image-provider.json   # 最近成功 provider（重试用）
```
