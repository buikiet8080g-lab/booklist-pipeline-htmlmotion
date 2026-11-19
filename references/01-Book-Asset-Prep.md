# 01 书籍核验 + 真实书封资产

**这一阶段的唯一产出是一张可核验的书封。** 没有它就不许进 05（D16）。

封面**由 Skill 自己搜**，用户只给书名：

```bash
python3 <skill>/ours/fetch_cover.py --book "被讨厌的勇气" --author "岸见一郎"
# 命中豆瓣 → 校验书名/短边≥300/长宽比 0.45–0.95 → images/cover-verified.jpg + metadata/cover-source.json
```

搜索顺序：豆瓣图书 suggest（中文书命中率最高）→ OpenLibrary（按 ISBN 备选）。都没有就阻塞并给出三条出路（换 ISBN / 写全名 / 手动放官方图），**绝不生成占位图或模型封面**。
`run_all.py --book "<书名>"` 会自动调用它，不需要单独跑。

## 怎么判断

| 要核的 | 判据 | 不过怎么办 |
|---|---|---|
| 书名 / 作者 / 出版社 / ISBN | 至少两项能对上同一版次（版权页、电商详情页、出版社官网任一） | 换版次或换书；不许「大概是这样」 |
| 书封图 | 能看清书名与作者；分辨率短边 ≥ 900px；是**扫描/实拍/官方图**，不是模型生成 | 换图。**不许**让图片模型生成封面，**不许**在图片阶段贴图修补（D16） |
| 引文页码 | 引文能在实体书/正版电子书对应页找到 | 找不到页码就留空，不许编（03 会拦） |

## 输出（下游真正读的）

```
01-book-assets.md                     # 人读：核验过程、来源链接、版次
images/cover-verified.jpg             # 机器读：全片唯一书封
metadata/book-assets.json             # 机器读：下面这个结构
```

```json
{
  "title": "被讨厌的勇气",
  "author": "岸见一郎 / 古贺史健",
  "publisher": "机械工业出版社",
  "isbn": "978-7-111-49541-3",
  "cover": "images/cover-verified.jpg",
  "cover_verified": true,
  "cover_source": "publisher_scan",
  "quote_page": "第 88 页",
  "tag": "豆瓣 8.6"
}
```

自动搜到的封面会写 `cover_source: douban:<id>`、`source_page`、`sha256`；`cover_verified: false` 时 `ours/lint_spec.py` 报黄（允许做样片，不允许发布）；`cover_source: model_generated` 报红。

## 闸门

```bash
python3 <skill>/ours/audit_book_cover_policy.py <项目>/metadata   # 书封政策（禁 model_generated / 禁贴图修补）
python3 <skill>/ours/lint_spec.py <项目>/metadata/plan.json       # 05 之后：书封文件存在 + 来源合规
```
