#!/bin/bash

# This file is intentionally small: all product logic lives in cleanup.py.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

clear
printf '\n  Claude 环境检查与清理\n'
printf '  ======================\n\n'

if [ "$(uname -s)" != "Darwin" ]; then
  printf '这个工具目前只支持 Mac。\n'
  printf '按回车退出……'
  read -r _
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf '这台 Mac 还缺少运行工具 Python 3。\n'
  printf '按回车后将打开官方下载页，安装后再双击本文件。\n'
  read -r _
  open "https://www.python.org/downloads/macos/"
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  printf '这台 Mac 上的 Python 版本太旧。\n'
  printf '按回车后将打开官方下载页，安装新版本后再双击本文件。\n'
  read -r _
  open "https://www.python.org/downloads/macos/"
  exit 1
fi

python3 "$SCRIPT_DIR/cleanup.py"
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
  printf '\n运行没有完成。请保留这个窗口的内容，联系帮你安装本工具的人。\n'
fi

printf '\n按回车关闭窗口……'
read -r _
exit "$STATUS"
