#!/bin/bash
# ロールバックスクリプト
# 使用方法: ./scripts/rollback.sh [backup_file]

set -e

# 設定
SERVER_HOST="162.43.33.37"
SERVER_USER="root"
SERVER_PASS="@hN5keQGc"
SERVER_DIR="/root/ansystem"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# バックアップファイルの指定
if [[ -n "$1" ]]; then
    BACKUP_FILE="$1"
else
    # 最新のバックアップを取得
    echo_info "利用可能なバックアップ一覧:"
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} \
        "ls -lt /root/backups/*.sql 2>/dev/null | head -10" || echo "バックアップが見つかりません"

    read -p "復元するバックアップファイル名を入力: " BACKUP_FILE
fi

if [[ -z "$BACKUP_FILE" ]]; then
    echo_error "バックアップファイルが指定されていません"
    exit 1
fi

echo_warn "データベースを ${BACKUP_FILE} から復元します"
read -p "本当に実行しますか？ (yes/NO): " confirm
if [[ "$confirm" != "yes" ]]; then
    echo_error "ロールバックを中止しました"
    exit 1
fi

# データベース復元
echo_info "データベース復元中..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} << EOF
cd ${SERVER_DIR}
docker compose exec -T db psql -U oza_user -d postgres -c "DROP DATABASE IF EXISTS oza_system;"
docker compose exec -T db psql -U oza_user -d postgres -c "CREATE DATABASE oza_system;"
docker compose exec -T db psql -U oza_user -d oza_system < /root/backups/${BACKUP_FILE}
EOF

# サービス再起動
echo_info "サービス再起動中..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} \
    "cd ${SERVER_DIR} && docker compose restart backend celery_worker celery_beat"

# ヘルスチェック
echo_info "ヘルスチェック中..."
sleep 10
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_HOST}:8000/admin/login/)
if [[ "$HTTP_CODE" == "200" ]]; then
    echo_info "ロールバック成功！ (HTTP $HTTP_CODE)"
else
    echo_error "ヘルスチェック失敗 (HTTP $HTTP_CODE)"
    exit 1
fi

echo_info "=== ロールバック完了 ==="
