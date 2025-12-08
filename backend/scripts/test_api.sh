#!/bin/bash
#
# API動作確認スクリプト
# OZAシステムのAPIエンドポイントをテストします
#
# 使用方法:
#   chmod +x scripts/test_api.sh
#   ./scripts/test_api.sh
#

set -e

BASE_URL="${API_BASE_URL:-http://localhost:8000}"
API_URL="$BASE_URL/api/v1"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 結果カウンタ
PASSED=0
FAILED=0

echo "============================================================"
echo "OZAシステム API動作確認スクリプト"
echo "============================================================"
echo "BASE_URL: $BASE_URL"
echo ""

# テスト関数
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5
    local auth_header=$6

    echo -n "テスト: $description ... "

    if [ -n "$auth_header" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $auth_header" \
            -d "$data" \
            "$API_URL$endpoint" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint" 2>&1)
    fi

    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}PASS${NC} (status: $status_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}FAIL${NC} (expected: $expected_status, got: $status_code)"
        echo "  Response: ${body:0:200}..."
        ((FAILED++))
        return 1
    fi
}

# 1. サーバー起動確認
echo ""
echo -e "${BLUE}=== サーバー起動確認 ===${NC}"
echo -n "サーバー接続テスト ... "
if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health/" | grep -q "200\|404"; then
    echo -e "${GREEN}OK${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC} - サーバーに接続できません"
    ((FAILED++))
    echo "サーバーが起動していることを確認してください"
    exit 1
fi

# 2. 認証テスト
echo ""
echo -e "${BLUE}=== 認証API テスト ===${NC}"

# ログイン成功
LOGIN_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@test-juku.com","password":"admin123"}' \
    "$API_URL/auth/login/")

if echo "$LOGIN_RESPONSE" | grep -q "access"; then
    echo -e "ログイン（正常） ... ${GREEN}PASS${NC}"
    ((PASSED++))
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access', ''))" 2>/dev/null || echo "")
    REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('refresh', ''))" 2>/dev/null || echo "")
else
    echo -e "ログイン（正常） ... ${RED}FAIL${NC}"
    echo "  Response: $LOGIN_RESPONSE"
    ((FAILED++))
    ACCESS_TOKEN=""
    REFRESH_TOKEN=""
fi

# ログイン失敗
test_endpoint "POST" "/auth/login/" \
    '{"email":"admin@test-juku.com","password":"wrongpassword"}' \
    "401" "ログイン（パスワード間違い）"

# 存在しないユーザー
test_endpoint "POST" "/auth/login/" \
    '{"email":"nonexistent@test.com","password":"test"}' \
    "401" "ログイン（存在しないユーザー）"

# トークンリフレッシュ
if [ -n "$REFRESH_TOKEN" ]; then
    test_endpoint "POST" "/auth/token/refresh/" \
        "{\"refresh\":\"$REFRESH_TOKEN\"}" \
        "200" "トークンリフレッシュ"
fi

# 3. /me エンドポイント
echo ""
echo -e "${BLUE}=== ユーザー情報API テスト ===${NC}"

if [ -n "$ACCESS_TOKEN" ]; then
    test_endpoint "GET" "/auth/me/" "" "200" "ユーザー情報取得（認証済み）" "$ACCESS_TOKEN"
fi

test_endpoint "GET" "/auth/me/" "" "401" "ユーザー情報取得（未認証）"

# 4. 生徒API
echo ""
echo -e "${BLUE}=== 生徒API テスト ===${NC}"

if [ -n "$ACCESS_TOKEN" ]; then
    test_endpoint "GET" "/students/" "" "200" "生徒一覧取得" "$ACCESS_TOKEN"
fi

# 5. 契約API
echo ""
echo -e "${BLUE}=== 契約API テスト ===${NC}"

if [ -n "$ACCESS_TOKEN" ]; then
    test_endpoint "GET" "/contracts/" "" "200" "契約一覧取得" "$ACCESS_TOKEN"
fi

# 6. 勤怠API
echo ""
echo -e "${BLUE}=== 勤怠API テスト ===${NC}"

if [ -n "$ACCESS_TOKEN" ]; then
    test_endpoint "GET" "/hr/attendances/" "" "200" "勤怠一覧取得" "$ACCESS_TOKEN"
fi

# 7. 校舎API
echo ""
echo -e "${BLUE}=== 校舎API テスト ===${NC}"

if [ -n "$ACCESS_TOKEN" ]; then
    test_endpoint "GET" "/schools/" "" "200" "校舎一覧取得" "$ACCESS_TOKEN"
fi

# 8. 学年・教科API
echo ""
echo -e "${BLUE}=== マスタAPI テスト ===${NC}"

if [ -n "$ACCESS_TOKEN" ]; then
    test_endpoint "GET" "/schools/grades/" "" "200" "学年一覧取得" "$ACCESS_TOKEN"
    test_endpoint "GET" "/schools/subjects/" "" "200" "教科一覧取得" "$ACCESS_TOKEN"
fi

# 9. API ドキュメント
echo ""
echo -e "${BLUE}=== API ドキュメント テスト ===${NC}"

echo -n "OpenAPI スキーマ ... "
SCHEMA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/schema/")
if [ "$SCHEMA_STATUS" = "200" ]; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}SKIP${NC} (status: $SCHEMA_STATUS)"
fi

echo -n "Swagger UI ... "
SWAGGER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/docs/")
if [ "$SWAGGER_STATUS" = "200" ]; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}SKIP${NC} (status: $SWAGGER_STATUS)"
fi

# 結果サマリー
echo ""
echo "============================================================"
echo -e "結果: ${GREEN}$PASSED PASSED${NC}, ${RED}$FAILED FAILED${NC}"
echo "============================================================"

if [ $FAILED -gt 0 ]; then
    echo -e "${YELLOW}警告: 一部のテストが失敗しました${NC}"
    exit 1
else
    echo -e "${GREEN}全てのテストがパスしました！${NC}"
    exit 0
fi
