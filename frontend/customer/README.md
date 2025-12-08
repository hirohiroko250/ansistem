# MyLesson - レッスン管理アプリケーション

MyLessonは、習い事の管理・予約・チケット購入などを一元管理できるモバイルファーストのWebアプリケーションです。

## 技術スタック

### フロントエンド
- **Framework**: Next.js 13.5.1 (App Router)
- **UI**: React 18.2.0
- **スタイリング**: Tailwind CSS 3.3.3
- **UIコンポーネント**: shadcn/ui (Radix UI)
- **アイコン**: Lucide React
- **フォーム管理**: React Hook Form + Zod
- **言語**: TypeScript 5.2.2

### バックエンド（予定）
- **Framework**: Django (REST API)
- **データベース**: Supabase (PostgreSQL)
- **認証**: Supabase Auth

## プロジェクト構成

```
project/
├── app/                          # Next.js App Router
│   ├── page.tsx                  # ホーム画面（ダッシュボード）
│   ├── login/                    # ログイン画面
│   ├── signup/                   # サインアップ画面
│   ├── password-reset/           # パスワードリセット画面
│   ├── feed/                     # フィード（投稿一覧）
│   ├── tickets/                  # チケット一覧
│   ├── ticket-purchase/          # チケット購入
│   ├── purchase-history/         # 購入履歴
│   ├── qr-reader/                # QRコード読み取り
│   ├── calendar/                 # カレンダー
│   ├── chat/                     # チャット
│   │   └── [id]/                 # 個別チャット画面
│   ├── children/                 # 子供管理
│   ├── class-registration/       # クラス登録
│   ├── trial/                    # 体験レッスン
│   ├── transfer-flow/            # 振替処理
│   ├── map/                      # 地図
│   ├── settings/                 # 設定
│   │   ├── profile-edit/         # プロフィール編集
│   │   └── payment/              # 支払い方法
│   ├── layout.tsx                # ルートレイアウト
│   └── globals.css               # グローバルスタイル
├── components/                   # Reactコンポーネント
│   ├── ui/                       # shadcn/uiコンポーネント
│   └── bottom-tab-bar.tsx        # ボトムタブナビゲーション
├── lib/                          # ユーティリティ・ヘルパー
│   ├── supabase.ts               # Supabase クライアント設定
│   ├── feed-data.ts              # フィードデータ（仮データ）
│   └── utils.ts                  # 汎用ユーティリティ
├── hooks/                        # カスタムフック
│   └── use-toast.ts              # トースト通知フック
├── supabase/                     # Supabase関連
│   └── migrations/               # データベースマイグレーション
├── .env                          # 環境変数
├── next.config.js                # Next.js設定
├── tailwind.config.ts            # Tailwind CSS設定
├── tsconfig.json                 # TypeScript設定
└── package.json                  # 依存関係
```

## 主要機能

### 認証
- メール/パスワード認証（Supabase Auth）
- サインアップ
- ログイン
- パスワードリセット
- ログアウト

### ホーム（ダッシュボード）
- 最新情報の表示
- 主要機能へのショートカット
- ボトムタブナビゲーション

### フィード
- ブランド別投稿フィルター（契約ブランド/全ブランド）
- 投稿への評価機能（1〜5の星評価）
- いいね機能
- コメント機能
- イベント告知
- チケット購入リンク

### チケット管理
- チケット一覧表示
- QRコード表示
- チケット購入
- 購入履歴

### カレンダー
- レッスンスケジュール表示
- 日別・月別表示

### チャット
- 質問・相談機能
- 個別チャット

### その他
- クラス登録
- 体験レッスン申し込み
- 子供情報管理
- 地図表示
- 設定管理

## Django バックエンド連携方法

### 1. API エンドポイント設計

Django側で以下のようなREST APIエンドポイントを実装してください：

```
/api/auth/
  POST /register          # ユーザー登録
  POST /login             # ログイン
  POST /logout            # ログアウト
  POST /password-reset    # パスワードリセット

/api/feed/
  GET  /posts             # 投稿一覧取得
  POST /posts/:id/like    # いいね
  POST /posts/:id/rate    # 評価

/api/tickets/
  GET  /                  # チケット一覧
  GET  /:id               # チケット詳細
  POST /purchase          # チケット購入
  GET  /history           # 購入履歴

/api/classes/
  GET  /                  # クラス一覧
  POST /register          # クラス登録
  GET  /schedule          # スケジュール取得

/api/chat/
  GET  /conversations     # 会話一覧
  GET  /:id/messages      # メッセージ取得
  POST /:id/messages      # メッセージ送信

/api/user/
  GET  /profile           # プロフィール取得
  PUT  /profile           # プロフィール更新
  GET  /children          # 子供一覧
  POST /children          # 子供追加
```

### 2. Next.js 側の API 連携実装

`lib/api.ts` を作成し、以下のようなAPI クライアントを実装：

```typescript
// lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export async function fetchPosts() {
  const response = await fetch(`${API_BASE_URL}/feed/posts`);
  if (!response.ok) throw new Error('Failed to fetch posts');
  return response.json();
}

export async function purchaseTicket(ticketData: any) {
  const response = await fetch(`${API_BASE_URL}/tickets/purchase`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ticketData),
  });
  if (!response.ok) throw new Error('Failed to purchase ticket');
  return response.json();
}
```

### 3. 環境変数設定

`.env.local` に以下を追加：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 4. Django CORS設定

Django側で `django-cors-headers` を設定：

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ...
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    # 本番環境のドメインも追加
]
```

### 5. 認証トークン管理

Supabase Authを使用する場合、以下のようにトークンをリクエストヘッダーに含める：

```typescript
import { supabase } from '@/lib/supabase';

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession();

  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${session?.access_token}`,
    },
  });
}
```

### 6. データ移行

現在 `lib/feed-data.ts` にある仮データをDjangoのデータベースに移行してください。

## セットアップ

### 前提条件
- Node.js 18.x以上
- npm または yarn
- Supabase アカウント

### インストール

```bash
# 依存関係のインストール
npm install

# 環境変数の設定
cp .env.example .env.local
# .env.local を編集してSupabase認証情報を設定

# 開発サーバーの起動
npm run dev
```

アプリケーションは `http://localhost:3000` で起動します。

### ビルド

```bash
# プロダクションビルド
npm run build

# ビルドしたアプリケーションの起動
npm start
```

## データベース

現在Supabaseを使用しています。以下のテーブルが作成されています：

- `users` - ユーザー情報
- 他のテーブルは必要に応じてマイグレーションファイルを確認してください

マイグレーションファイルは `supabase/migrations/` にあります。

## デプロイ

### Vercel（推奨）
Next.jsアプリケーションはVercelに簡単にデプロイできます：

```bash
vercel
```

### その他のプラットフォーム
- Docker
- AWS
- Netlify
など、Node.jsアプリケーションをサポートする任意のプラットフォームで動作します。

## 開発ガイドライン

### コーディング規約
- TypeScriptを使用
- コンポーネントは関数コンポーネントで記述
- Tailwind CSSでスタイリング
- クライアントコンポーネントには `'use client'` ディレクティブを使用

### ファイル命名規則
- コンポーネント: `kebab-case.tsx`
- ページ: `page.tsx`
- レイアウト: `layout.tsx`

## トラブルシューティング

### ビルドエラー
```bash
npm run typecheck  # 型チェック
npm run lint       # リントチェック
```

### 環境変数が読み込まれない
- `.env.local` ファイルが存在するか確認
- 開発サーバーを再起動

## ライセンス

Private

## サポート

問題や質問がある場合は、開発チームにお問い合わせください。
