# 社員チャット機能改善計画

## 概要
現在のポーリング方式チャットをSlack/Chatwork風のリアルタイムチャットに改善する

---

## Phase 1: リアルタイム通信（WebSocket導入） ✅ 完了

### 1.1 バックエンド - Django Channels導入
- [x] django-channels パッケージインストール
- [x] channels-redis パッケージインストール（既存Redisを活用）
- [x] ASGI設定（config/asgi.py）の作成・更新
- [x] WebSocket用のrouting設定（apps/communications/routing.py）

### 1.2 バックエンド - Consumer実装
- [x] ChatConsumer クラス作成（apps/communications/consumers.py）
  - [x] connect: 認証・チャンネル参加
  - [x] disconnect: チャンネル離脱
  - [x] receive: メッセージ受信・ブロードキャスト
  - [x] send_message: メッセージ送信処理
- [x] JWT認証ミドルウェア（WebSocket用）
- [x] チャンネルグループ管理（channel_layer.group_add/send）

### 1.3 バックエンド - 既存API連携
- [x] MessageViewSet.create() にWebSocket通知追加
- [x] メッセージ編集時のWebSocket通知
- [x] メッセージ削除時のWebSocket通知
- [ ] 既読更新時のWebSocket通知（次回実装）
- [ ] 新規チャンネル作成時の通知（次回実装）

### 1.4 フロントエンド - WebSocketクライアント
- [x] WebSocket接続管理クラス/フック作成（lib/websocket.ts）
  - [x] 接続・再接続ロジック
  - [x] 認証トークン送信
  - [x] ハートビート（ping/pong）
- [x] useChatWebSocket Reactフック作成
- [ ] 既存ポーリング処理の削除（チャット画面統合時に実施）
- [ ] リアルタイムメッセージ受信処理（チャット画面統合時に実施）

### 1.5 Docker設定
- [x] docker-compose.yml にDaphne設定追加
- [x] WebSocketポート公開（ws://）
- [ ] Nginx設定（プロキシ）- 本番環境時に実施

---

## Phase 2: PCレイアウト改善（左サイドバー固定） ✅ 完了

### 2.1 レイアウト構造
- [x] レスポンシブ対応の2カラムレイアウト
  - [x] PC: 左サイドバー（チャンネル一覧）+ 右メイン（メッセージ）
  - [x] モバイル: 現状維持（一覧→詳細の遷移）
- [x] ブレークポイント設定（md: 768px以上で2カラム）

### 2.2 サイドバーコンポーネント
- [x] ChatSidebar.tsx 作成
  - [x] チャンネル一覧（タブ切り替え）
  - [x] 検索バー
  - [x] 新規チャット作成ボタン
  - [x] 選択状態のハイライト
- [x] チャンネルアイテムコンポーネント（ChatSidebar内）

### 2.3 メッセージエリアコンポーネント
- [x] ChatMessages.tsx 分離
  - [x] ヘッダー（チャンネル名・アクション）
  - [x] メッセージリスト
  - [x] 入力エリア
  - [x] タイピングインジケータ表示
- [x] 空状態（チャンネル未選択時）の表示

### 2.4 WebSocket統合
- [x] useChatWebSocketフックを統合
- [x] リアルタイムメッセージ受信
- [x] WebSocket接続時はポーリング無効化

---

## Phase 3: スレッド機能 ✅ 完了

### 3.1 バックエンド
- [x] Message.reply_to フィールド活用（既存）
- [x] スレッドメッセージ取得API
  - [x] GET /messages/{msg_id}/thread/
- [x] スレッド返信カウント追加（reply_count）
- [x] WebSocketスレッド返信通知（notify_thread_reply）

### 3.2 フロントエンド
- [x] スレッド表示UI
  - [x] メッセージに「返信」ボタン追加（ホバー時表示）
  - [x] スレッドパネル（PC: 右サイドパネル、モバイル: ボトムシート）
  - [x] スレッド内メッセージ一覧
- [x] スレッド返信入力フォーム
- [x] 親メッセージに返信数バッジ表示
- [x] WebSocketでリアルタイム返信数更新

---

## Phase 4: リアクション機能 ✅ 完了

### 4.1 バックエンド - モデル追加
- [x] MessageReaction モデル作成
- [x] マイグレーション作成・実行

### 4.2 バックエンド - API
- [x] POST /messages/{id}/reactions/ - リアクション追加
- [x] DELETE /messages/{id}/reactions/{emoji}/ - リアクション削除
- [x] MessageSerializer にリアクション一覧追加
- [x] WebSocketリアクション通知

### 4.3 フロントエンド
- [x] 絵文字ピッカーコンポーネント導入
- [x] メッセージホバー時にリアクションボタン表示
- [x] リアクションバッジ表示（メッセージ下部）
- [x] リアクション追加・削除処理

---

## Phase 5: メンション機能 ✅ 完了

### 5.1 バックエンド
- [x] メンションパーサー実装（@[user_id] 検出）
- [x] MessageMention モデル追加
- [x] メンション時の通知作成（Notification）
- [x] WebSocketでメンション通知送信
- [x] メンション可能ユーザー取得API

### 5.2 フロントエンド
- [x] 入力時の@補完UI（オートコンプリート）
- [x] メンション表示のハイライト（青色リンク）
- [x] MentionInputコンポーネント

---

## Phase 6: ファイル添付機能 ✅ 完了

### 6.1 バックエンド
- [x] ファイルアップロードAPI
  - [x] POST /messages/upload/
  - [x] 対応形式: 画像（jpg, png, gif, webp）、ドキュメント（pdf, doc, docx, xls, xlsx, ppt, pptx, txt, csv）
  - [x] ファイルサイズ制限（10MB）
- [x] ローカルストレージ設定（chat_attachments/）
- [x] Message.attachment_url, attachment_name 活用

### 6.2 フロントエンド
- [x] ファイル選択UI（ボタン + ドラッグ&ドロップ対応）
- [x] アップロード進捗表示
- [x] 画像プレビュー表示（拡大モーダル付き）
- [x] ファイルダウンロードリンク

---

## Phase 7: チャンネル管理機能 ✅ 完了

### 7.1 バックエンド
- [x] チャンネル更新API強化
  - [x] PUT /channels/{id}/settings/ - 名前・説明変更
  - [x] POST /channels/{id}/members/ - メンバー追加
  - [x] DELETE /channels/{id}/members/{user_id}/ - メンバー削除
  - [x] PUT /channels/{id}/members/{user_id}/role/ - ロール変更
- [x] 権限チェック（ADMINのみ変更可）

### 7.2 フロントエンド
- [x] チャンネル設定モーダル（ChannelSettingsModal.tsx）
  - [x] チャンネル名編集
  - [x] 説明編集
  - [x] メンバー一覧表示
  - [x] メンバー追加・削除
  - [x] ロール変更（ADMIN/MEMBER/READONLY）
- [ ] チャンネル作成モーダル改善（次回実装）
  - [ ] パブリック/プライベート選択
  - [ ] 初期メンバー選択

---

## Phase 8: 検索機能強化 ✅ 完了

### 8.1 バックエンド
- [x] メッセージ全文検索API
  - [x] GET /messages/search/?q=keyword
  - [x] PostgreSQL全文検索（simple config）+ icontainsフォールバック
- [x] 検索結果ハイライト（[[HIGHLIGHT]]マーカー）
- [x] 日付・送信者フィルター（date_from, date_to, sender_id, channel_id）

### 8.2 フロントエンド
- [x] グローバル検索ボタン（ChatSidebarヘッダー）
- [x] 検索パネル（SearchPanel.tsx）
  - [x] キーワード入力
  - [x] 日付範囲フィルター
  - [x] 現在のチャンネルのみ検索オプション
- [x] 検索結果一覧表示（ハイライト付き）
- [x] 検索結果からチャンネルへジャンプ
- [ ] 検索履歴（次回実装）

---

## 実装優先順位

| 優先度 | Phase | 理由 |
|--------|-------|------|
| 高 | Phase 1 | リアルタイム通信は基盤機能 |
| 高 | Phase 2 | PC利用時のUX大幅改善 |
| 中 | Phase 3 | Slack風の重要機能 |
| 中 | Phase 6 | 実用性向上 |
| 中 | Phase 7 | 運用に必要 |
| 低 | Phase 4 | あると便利 |
| 低 | Phase 5 | あると便利 |
| 低 | Phase 8 | 大量メッセージ時に必要 |

---

## 技術スタック追加

### バックエンド
- django-channels >= 4.0
- channels-redis >= 4.0
- daphne または uvicorn[standard]

### フロントエンド
- 追加ライブラリなし（WebSocket はブラウザネイティブ）
- 絵文字ピッカー: emoji-mart（Phase 4で追加）

---

## 注意事項

1. **後方互換性**: 既存のREST APIは維持し、WebSocketは追加機能として実装
2. **段階的移行**: ポーリング→WebSocketは段階的に移行可能に
3. **エラーハンドリング**: WebSocket切断時のフォールバック（ポーリング）
4. **テスト**: 各Phase完了後に統合テスト実施
5. **ドキュメント**: API仕様書の更新

---

## 作成日
2026-01-06

## 更新履歴
- 2026-01-06: 初版作成
- 2026-01-06: Phase 1 実装完了（WebSocket基盤）
- 2026-01-06: Phase 2 実装完了（PCレイアウト改善）
- 2026-01-06: Phase 3 実装完了（スレッド機能）
- 2026-01-06: Phase 4 実装完了（リアクション機能）
- 2026-01-06: Phase 5 実装完了（メンション機能）
- 2026-01-06: Phase 6 実装完了（ファイル添付機能）
- 2026-01-06: Phase 7 実装完了（チャンネル管理機能）
- 2026-01-06: Phase 8 実装完了（検索機能強化）
