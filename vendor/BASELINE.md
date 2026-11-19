# vendor 基线

| 项 | 值 |
|---|---|
| 上游 | https://github.com/alchaincyf/huashu-art-motion |
| 许可 | MIT（见 `vendor/huashu-art-motion/LICENSE`） |
| 基线 tag | **v1.2.0** |
| 基线 commit | `8f0a349`（v1.2.0：新增敦煌壁画，风格演示重做，解说动画语法更稳） |
| 获取方式（在线） | `git clone --depth 1 --branch v1.2.0 https://github.com/alchaincyf/huashu-art-motion vendor/huashu-art-motion` |
| 获取方式（离线兜底） | `cp -R /root/.pi/agent/skills/huashu-art-motion vendor/huashu-art-motion` 然后见下方「离线副本」 |
| 体积 | 仓库 144M；`scripts/engine` **24M**（其中 `lib/fonts` 16M）；与规格书 §15.2 一致 |
| 只读 | **是**。`vendor/` 一个字节不许改；所有改动只在 `patches/` |

## 校验

```bash
cd vendor/huashu-art-motion
git describe --tags            # 期望 v1.2.0
git status --porcelain         # 期望空
du -sh scripts/engine          # 期望 24M
```

## 离线副本（无网络时）

离线拿到的目录没有 `.git`，`patches/apply.sh` 需要 git 工作树才能 `git apply` 后可用 `git status` 校验。
在副本里补一个本地基线提交即可，**不改任何文件内容**：

```bash
cp -R /root/.pi/agent/skills/huashu-art-motion vendor/huashu-art-motion
cd vendor/huashu-art-motion
git init && git add -A && git commit -m "offline baseline v1.2.0"
git tag v1.2.0
```

此时 `git describe --tags` 输出 `v1.2.0`，`git status` 干净，`patches/apply.sh` 可正常重放。
离线副本无上游历史，升级需重新联网 clone 后再重放 patch。

## 上游有什么（只当资产，不当架构）

- `scripts/engine/`：`render.py --spec` 渲染器 + `clip.js` 片段运行时 + `clips/*.js` 8 个语法 + `lib/*.js` 绘图/排版库（含 `lib/fonts/` 16M 字体，OFL）
- `scripts/engine/lib/fonts/NotoSansSC-{500,700,800,900}.woff`、`NotoSerifSC-sub.woff`：本 Skill 直接引用，不另下字体
- `references/`：镜头表模板、动画语法卡、风格配方 57 张（**只读判据，不搬引擎**）
- 我们**不用**的：`eras*.js` 段落表/整片模式、`CAM` 世界画布、角色 rig、`three.min.js`、`scenes/`（风格配方）
