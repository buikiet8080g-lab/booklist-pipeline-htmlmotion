# 色板预设（huashu 8 套，同片只用一套）

## 8 套色板

| name | bg | surface | ink | sub | accent | accent2 | 题材 |
|---|---|---|---|---|---|---|---|
| `paper` | #F3EDE2 | #FBF8F2 | #1B1A17 | #6B655B | #C8402F | #2F5D62 | 纸本：人文、历史、读书（默认） |
| `poster` | #FFD23F | #FFF6D6 | #111111 | #4A4433 | #FF5A36 | #14213D | 海报黄：强观点、清单 |
| `ink` | #121417 | #1E2226 | #F2EFE8 | #A39E93 | #F2B33D | #5FB3A1 | 深墨：沉重/历史/战争 |
| `navy` | #0D1B2A | #16293D | #EEF3F6 | #8FA3B3 | #5CC8E0 | #F2A93B | 海军：数据、商业 |
| `bauhaus` | #EFE9DD | #FFFFFF | #111111 | #555555 | #D62828 | #1D4E89 | 包豪斯：数据密集 |
| `snow` | #E9EEF0 | #FFFFFF | #1F2A30 | #5E6B72 | #D9482B | #3E7C8C | 雪原：健康养生 |
| `wood` | #EDE3D1 | #F7F1E6 | #2B2622 | #7A6E62 | #C4552D | #3F5B4B | 暖木：家庭教育（默认） |
| `chalk` | #23302B | #2E3D37 | #F1EFE6 | #A9B3AA | #F4D35E | #E87D5A | 黑板：推导、讲解 |

## 规则

- **同片一套**：`plan.json` 顶层 `theme` + 每镜 `theme` 必须一致（`lint_spec` E01）。
- **禁 `data.palette` 整覆盖**：实测会把背景巨型序号和进度轨变成不可见（E10）。
- **禁蓝紫区**：色相 225–300 且饱和度 ≥0.30（E15 / 动态 D04）。
- 只允许改 accent 单键（`spec.theme` 写 `{"name":"wood","accent":"#..."}`）；改之前先确认不在蓝紫区。
- 图表的底和相邻镜同色板（`t3` 的 `data.theme` 不要另写）。

## 题材 → 色板

| 题材 | 首选 | 备选 |
|---|---|---|
| 家庭教育 / 亲子沟通 | `wood` | `paper` |
| 历史文学 / 传统文化 | `paper` | `ink` |
| 健康养生 | `snow` | `paper` |
| 数据密集 / 商业 | `bauhaus` | `paper` |
| 强观点 / 清单式 | `poster` | `bauhaus` |
| 推导 / 讲解 | `chalk` | `paper` |

## 新增色板（不推荐）

真要做账号专属色板：抽 6 色 → 写进本文件 → 检查无蓝紫 → 在 `lint_spec.py` 的 `PALETTES` 里登记。
工作量 0.5–1 天/风格（§16.5）。第一期不做。
