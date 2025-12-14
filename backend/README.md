# OZA System Backend

塾管理統合システム OZA System のバックエンドAPI

## 技術スタック

### Backend
- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Task Queue**: Celery
- **Authentication**: JWT (SimpleJWT)
- **API Documentation**: drf-spectacular (OpenAPI 3.0)

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Mobile**: Capacitor (iOS/Android)

---

## プロジェクト全体構成

```
アンシステム/
├── backend/                   # Django REST API
├── frontend/
│   ├── customer/              # 保護者・生徒向けアプリ
│   ├── admin/                 # 管理者向けアプリ
│   └── syain/                 # 社員・講師向けアプリ
├── docker-compose.yml         # 全体のDocker Compose
└── .env                       # 環境変数
```

---

## Backend ディレクトリ構成

```
backend/
├── api/
│   └── v1/                    # API v1 ルーティング
├── apps/
│   ├── [app_name]/            # 各機能アプリケーション (例: students, schools)
│   │   ├── models.py          # データベースモデル定義
│   │   ├── serializers.py     # APIデータの変換・バリデーション
│   │   ├── views.py           # リクエスト処理ロジック (ViewSets)
│   │   ├── urls.py            # アプリ内のルーティング
│   │   ├── admin.py           # Django管理画面の設定
│   │   ├── services/          # ビジネスロジック・複雑な処理
│   │   └── tasks.py           # Celeryタスク (非同期処理)
│   ├── core/                  # 共通機能
│   ├── tenants/               # テナント管理
│   ├── authentication/        # 認証
│   └── ... (contracts, lessons, etc.)
├── config/
│   ├── settings/
│   │   ├── base.py           # 共通設定
│   │   ├── development.py    # 開発環境
│   │   └── production.py     # 本番環境
│   ├── urls.py
│   └── celery.py
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── scripts/                   # データインポート/管理スクリプト
├── templates/                 # メールテンプレート等
├── tests/                     # テストコード
├── docker-compose.yml         # 本番用
└── ...
```

---

## Frontend ディレクトリ構成

### customer/ - 保護者・生徒向けアプリ

```
frontend/customer/
├── app/                       # Next.js App Router
│   ├── [feature]/             # 各機能ページ (calendar, chat, etc.)
│   │   ├── page.tsx           # ページコンポーネント
│   │   └── layout.tsx         # レイアウト
│   ├── login/                 # ログイン関連
│   └── ...
├── components/                # コンポーネント
│   ├── ui/                    # 汎用UIコンポーネント (shadcn/ui - Button, Input, etc.)
│   ├── [feature]/             # 機能特有のコンポーネント
│   │   ├── calendar-agent.tsx
│   │   └── ...
│   └── ...
├── lib/                       # ユーティリティ・ライブラリ
│   ├── api/                   # APIクライアント・定義
│   ├── utils.ts               # 共通ユーティリティ関数
│   └── ...
├── hooks/                     # カスタムフック
├── ios/                       # Capacitor iOS プロジェクト
├── android/                   # Capacitor Android プロジェクト
└── public/                    # 静的ファイル (画像など)
```

### admin/ - 管理者向けアプリ

```
frontend/admin/
├── app/                       # Next.js App Router
│   ├── dashboard/             # ダッシュボード
│   ├── students/              # 生徒管理機能
│   └── ...
├── components/
│   ├── ui/                    # 共通UIパーツ
│   └── ...
└── lib/
```

### syain/ - 社員・講師向けアプリ

```
frontend/syain/
├── app/                       # Next.js App Router
│   ├── home/                  # ホーム画面
│   ├── attendance/            # 出勤管理
│   └── ...
├── components/
├── lib/
└── supabase/                  # Supabase設定 (一部機能で使用)
```

## モデル構成

| テーブル | モデル | 説明 |
|----------|--------|------|
| T03 | Product | 商品マスタ（授業料・教材費・諸経費） |
| T05 | ProductPrice | 商品料金（月別料金） |
| T06 | ProductSet | 商品セット（入会金+教材費+授業料） |
| T07 | Discount | 割引マスタ |
| T08 | Course | コースマスタ |
| T09 | Pack | パックマスタ（複数コースセット） |
| T11 | Seminar | 講習マスタ |
| T12 | Certification | 検定マスタ |

## セットアップ

### 1. 環境変数

```bash
cp .env.example .env
# .env を編集
```

### 2. Docker で起動（推奨）

```bash
# 開発環境
make docker-up

# 本番環境
make docker-prod-up
```

### 3. ローカルで起動

```bash
# 依存関係インストール
make install

# マイグレーション
make migrate

# 開発サーバー起動
make dev
```

### 4. スーパーユーザー作成

```bash
make superuser
```

## API エンドポイント

| パス | 説明 |
|------|------|
| `/api/v1/auth/` | 認証（ログイン・トークン更新） |
| `/api/v1/schools/` | 校舎・ブランド・学年 |
| `/api/v1/students/` | 生徒・保護者 |
| `/api/v1/contracts/` | 契約・商品・コース |
| `/api/v1/lessons/` | 授業・スケジュール |
| `/api/v1/hr/` | 人事・勤怠 |
| `/api/v1/communications/` | チャット・通知 |
| `/api/v1/pricing/` | 料金計算 |
| `/api/v1/users/` | ユーザー管理 |
| `/api/v1/tenants/` | テナント管理 |

### API ドキュメント

- Swagger UI: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`
- OpenAPI Schema: `http://localhost:8000/api/schema/`

## 料金計算エンジン

`apps/pricing/services/pricing_engine.py`

### 計算ルール

| 項目 | ルール |
|------|--------|
| 初月料金 | 「X月入会者」列の金額 |
| 2ヶ月目以降 | 「X月」列の月額料金 |
| 追加チケット | 月額 ÷ 3.3 × 枚数（四捨五入） |
| 税区分 | 1,2=課税（+10%）, 3=非課税 |
| 3.3計算なし | 入会金・教材費・入会時教材費 |

### API 例

```bash
# 料金プレビュー
curl -X POST http://localhost:8000/api/v1/pricing/preview/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "courseId": "uuid",
    "enrollmentDate": "2024-04-15",
    "targetMonth": 4,
    "targetYear": 2024,
    "additionalTickets": 2
  }'
```

## 開発コマンド

```bash
# テスト
make test

# Lint
make lint

# フォーマット
make format

# Django Shell
make shell

# マイグレーション作成
make makemigrations

# キャッシュクリア
make clean
```

## Docker コマンド

```bash
# 開発環境
make docker-up       # 起動
make docker-down     # 停止
make docker-logs     # ログ確認

# 本番環境
make docker-prod-up
make docker-prod-down
make docker-prod-logs
```

## ポート

| サービス | ポート |
|----------|--------|
| Django API | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |

## 認証

JWT (JSON Web Token) を使用

```bash
# ログイン
POST /api/v1/auth/login/
{
  "email": "user@example.com",
  "password": "password"
}

# レスポンス
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}

# APIリクエスト
Authorization: Bearer {access_token}
```

## マルチテナント

リクエストヘッダーでテナントを指定:

```
X-Tenant-ID: {tenant_id}
```

## ライセンス

Proprietary - All Rights Reserved
