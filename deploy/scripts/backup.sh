#!/bin/bash
# 数据平台 Jupyter 备份脚本
# 用法：./deploy/scripts/backup.sh [目标目录]   （默认 ./backups）
# 建议配 crontab：0 2 * * * /path/to/deploy/scripts/backup.sh >> /var/log/jupyter-backup.log 2>&1
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="${1:-$SRC_DIR/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST"

# 1) 用户 notebook（含每用户目录与 shared）
tar czf "$DEST/notebooks-$STAMP.tar.gz" -C "$SRC_DIR" notebooks

# 2) 部署配置（.env 含 token，备份文件需异地加密存放）
tar czf "$DEST/deploy-$STAMP.tar.gz" -C "$SRC_DIR" \
    docker-compose.yml .env

# 3) 只保留最近 14 份，防磁盘被备份写满
ls -1t "$DEST"/notebooks-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
ls -1t "$DEST"/deploy-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f

echo "备份完成：$DEST ($STAMP)"
