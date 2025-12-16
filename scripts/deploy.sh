#!/bin/bash
# サーバーデプロイスクリプト
# 使用方法: ./scripts/deploy.sh

set -e

# 設定
SERVER_HOST="162.43.33.37"
SERVER_USER="root"
SERVER_PASS="@hN5keQGc"
SERVER_DIR="/root/ansystem"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. ローカルでのチェック
echo_info "=== ローカル環境チェック ==="

# 未コミットの変更確認
if [[ -n $(git status --porcelain) ]]; then
    echo_warn "未コミットの変更があります:"
    git status --short
    read -p "続行しますか？ (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo_error "デプロイを中止しました"
        exit 1
    fi
fi

# ローカルテスト
echo_info "ローカルでマイグレーションチェック..."
if ! docker compose run --rm backend python manage.py migrate --check 2>/dev/null; then
    echo_warn "適用されていないマイグレーションがあります"
    read -p "続行しますか？ (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo_error "デプロイを中止しました"
        exit 1
    fi
fi

# 2. サーバーへのデプロイ
echo_info "=== サーバーデプロイ開始 ==="

# サーバーでバックアップ作成
echo_info "データベースバックアップ作成中..."
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} \
    "cd ${SERVER_DIR} && docker compose exec -T db pg_dump -U oza_user oza_system > /root/backups/${BACKUP_FILE} 2>/dev/null || mkdir -p /root/backups && docker compose exec -T db pg_dump -U oza_user oza_system > /root/backups/${BACKUP_FILE}"
echo_info "バックアップ完了: /root/backups/${BACKUP_FILE}"

# コードをプッシュ
echo_info "GitHubにプッシュ中..."
git push origin main

# サーバーでコードを取得
echo_info "サーバーでコード取得中..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} \
    "cd ${SERVER_DIR} && git fetch origin && git reset --hard origin/main"

# Dockerイメージ再ビルド
echo_info "Dockerイメージ再ビルド中..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} \
    "cd ${SERVER_DIR} && docker compose build --no-cache backend"

# マイグレーション実行
echo_info "マイグレーション実行中..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} \
    "cd ${SERVER_DIR} && docker compose run --rm backend python manage.py migrate --settings=config.settings.production"

# サービス再起動
echo_info "サービス再起動中..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} \
    "cd ${SERVER_DIR} && docker compose up -d"

# ヘルスチェック
echo_info "ヘルスチェック中..."
sleep 10
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_HOST}:8000/admin/login/)
if [[ "$HTTP_CODE" == "200" ]]; then
    echo_info "デプロイ成功！ (HTTP $HTTP_CODE)"
else
    echo_error "ヘルスチェック失敗 (HTTP $HTTP_CODE)"
    echo_warn "ロールバックが必要な場合: ./scripts/rollback.sh"
    exit 1
fi

echo_info "=== デプロイ完了 ==="
echo_info "管理画面: http://${SERVER_HOST}:8000/admin/"
