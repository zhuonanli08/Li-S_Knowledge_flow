#!/usr/bin/env bash
# 云端第一次用 Blender 时运行一次：装 Blender 的 Python 版（bpy），不需要显卡和图形界面。
set -e
cd "$(dirname "$0")"
if [ -x .venv/bin/python ] && .venv/bin/python -c "import bpy" 2>/dev/null; then echo "bpy 已可用"; exit 0; fi
# bpy 依赖的系统库（装不上先跳过，import 报错时再按缺的库补）
(apt-get update -qq && apt-get install -y -qq libxrender1 libxxf86vm1 libxfixes3 libxi6 libxkbcommon0 libsm6 libgl1 libegl1) || echo "系统库安装失败，继续"
# bpy 只发特定 Python 版本的包：建 3.11 环境，uv 会挑能装的最新 bpy
uv venv -q -p 3.11 .venv
uv pip install -q -p .venv/bin/python bpy
.venv/bin/python -c "import bpy; print('bpy', bpy.app.version_string)"
