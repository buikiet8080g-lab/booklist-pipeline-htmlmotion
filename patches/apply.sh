#!/usr/bin/env bash
# 顺序应用全部 patch 到 vendor 副本。fail-fast：任何一个 --check 不过就停，不动后面的。
# 用法：./patches/apply.sh [vendor 目录]（默认 ../vendor/huashu-art-motion）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VENDOR="${1:-$HERE/../vendor/huashu-art-motion}"
cd "$VENDOR"
[ -d .git ] || { echo "✗ $VENDOR 不是 git 工作树：离线副本要先 git init + 一次基线提交（见 vendor/BASELINE.md）" >&2; exit 2; }
n=0
for p in "$HERE"/0*.patch; do
  name="$(basename "$p")"
  if ! git apply --check "$p" 2>/dev/null; then
    echo "✗ $name 打不上（vendor 已被改过或上游升级后冲突）。已应用的：$n 个" >&2
    git apply --check "$p" >&2 || true
    exit 1
  fi
  git apply "$p"
  n=$((n + 1))
  echo "✓ $name"
done
echo "patches applied: $n"
