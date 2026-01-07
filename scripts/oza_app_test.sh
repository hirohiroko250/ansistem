#!/bin/bash
# OZA App 自動動作確認スクリプト
# Usage: ./oza_app_test.sh

APP_ID="com.mylesson.app"
OUTPUT_DIR="./test_results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "🧪 OZA App 自動テスト開始"
echo "📁 結果保存先: $OUTPUT_DIR"
echo ""

# 1. アプリ起動
echo "1️⃣ アプリを起動..."
adb shell am force-stop $APP_ID
sleep 1
adb shell am start -n $APP_ID/.MainActivity
sleep 3

# 2. 起動画面のスクリーンショット
echo "2️⃣ 起動画面をキャプチャ..."
adb exec-out screencap -p > "$OUTPUT_DIR/01_launch.png"
echo "   ✅ 01_launch.png 保存"

# 3. 画面情報取得
echo "3️⃣ UI階層を取得..."
adb shell uiautomator dump /sdcard/ui_dump.xml
adb pull /sdcard/ui_dump.xml "$OUTPUT_DIR/ui_hierarchy.xml" 2>/dev/null
echo "   ✅ ui_hierarchy.xml 保存"

# 4. 画面タップテスト（中央をタップ）
echo "4️⃣ 画面インタラクションテスト..."
# 画面サイズ取得
SCREEN_SIZE=$(adb shell wm size | grep -oE '[0-9]+x[0-9]+')
WIDTH=$(echo $SCREEN_SIZE | cut -d'x' -f1)
HEIGHT=$(echo $SCREEN_SIZE | cut -d'x' -f2)
CENTER_X=$((WIDTH / 2))
CENTER_Y=$((HEIGHT / 2))

# 下にスワイプ
adb shell input swipe $CENTER_X $((HEIGHT * 2 / 3)) $CENTER_X $((HEIGHT / 3)) 300
sleep 2
adb exec-out screencap -p > "$OUTPUT_DIR/02_after_scroll.png"
echo "   ✅ 02_after_scroll.png 保存"

# 5. 戻るボタンテスト
echo "5️⃣ 戻るボタンテスト..."
adb shell input keyevent KEYCODE_BACK
sleep 2
adb exec-out screencap -p > "$OUTPUT_DIR/03_after_back.png"
echo "   ✅ 03_after_back.png 保存"

# 6. ホームボタンテスト
echo "6️⃣ ホームボタンテスト..."
adb shell input keyevent KEYCODE_HOME
sleep 1

# 7. アプリ再起動
echo "7️⃣ アプリ再起動テスト..."
adb shell am start -n $APP_ID/.MainActivity
sleep 3
adb exec-out screencap -p > "$OUTPUT_DIR/04_restart.png"
echo "   ✅ 04_restart.png 保存"

# 結果サマリー
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ テスト完了！"
echo ""
echo "📸 スクリーンショット:"
ls -la "$OUTPUT_DIR"/*.png 2>/dev/null
echo ""
echo "📂 結果フォルダ: $OUTPUT_DIR"
echo ""
echo "Finderで開く: open $OUTPUT_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
