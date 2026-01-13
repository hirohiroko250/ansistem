#!/bin/bash
# 料金計算テスト実行スクリプト

set -e

echo "=========================================="
echo "料金計算テスト実行"
echo "=========================================="

# 色付きログ
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. バックエンド単体テスト
echo -e "\n${YELLOW}[1/3] バックエンド単体テスト${NC}"
cd backend
if python -m pytest tests/pricing/ -v --tb=short; then
    echo -e "${GREEN}✓ バックエンドテスト成功${NC}"
else
    echo -e "${RED}✗ バックエンドテスト失敗${NC}"
    exit 1
fi
cd ..

# 2. ゴールデンテスト
echo -e "\n${YELLOW}[2/3] ゴールデンテスト${NC}"
cd backend
if python -m pytest tests/pricing/test_pricing_golden.py -v; then
    echo -e "${GREEN}✓ ゴールデンテスト成功${NC}"
else
    echo -e "${RED}✗ ゴールデンテスト失敗${NC}"
    exit 1
fi
cd ..

# 3. E2Eテスト（オプション）
if [ "$1" == "--e2e" ]; then
    echo -e "\n${YELLOW}[3/3] E2Eテスト${NC}"
    cd e2e
    npm install
    npx playwright test --project=chromium
    cd ..
fi

echo -e "\n${GREEN}=========================================="
echo "全テスト完了"
echo "==========================================${NC}"
