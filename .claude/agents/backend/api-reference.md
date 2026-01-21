# API Reference - エンドポイント一覧

このプロジェクトの全APIエンドポイントと責務を整理したリファレンス。

## 認証方式
- **JWT（JSON Web Token）**: SimpleJWT使用
- **ヘッダー**: `Authorization: Bearer <access_token>`
- **権限チェック**:
  - `IsAuthenticated`: 認証済みユーザーのみ
  - `IsTenantUser`: 同じテナント内のユーザーのみ
  - `IsTenantAdmin`: テナント管理者のみ
  - `AllowAny`: 認証不要

---

## 1. authentication（認証）- `/api/v1/auth/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `login/` | POST | ログイン、JWTトークン発行 | 不要 |
| `register/` | POST | ユーザー登録（保護者・生徒） | 不要 |
| `register/employee/` | POST | 社員登録（承認待ち） | 不要 |
| `check-email/` | POST | メールアドレス重複チェック | 不要 |
| `check-phone/` | POST | 電話番号重複チェック | 不要 |
| `logout/` | POST | ログアウト | 必要 |
| `token/refresh/` | POST | アクセストークンリフレッシュ | 不要 |
| `password-reset/` | POST | パスワードリセット申請 | 不要 |
| `password-reset/confirm/` | POST | パスワードリセット確認 | 不要 |
| `password-change/` | POST | パスワード変更 | 必要 |
| `me/` | GET, PATCH | ユーザー情報取得・更新 | 必要 |
| `impersonate-guardian/` | POST | 保護者としてログイン（管理者用） | 必要 |

---

## 2. users（ユーザー）- `/api/v1/users/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `/` | GET, POST | ユーザー一覧・作成（管理者） | 必要 |
| `{id}/` | GET, PUT, DELETE | ユーザー詳細・更新・削除 | 必要 |
| `{id}/activate/` | POST | ユーザー有効化 | 必要 |
| `{id}/deactivate/` | POST | ユーザー無効化 | 必要 |
| `profile/` | GET, PATCH, POST | プロフィール取得・更新・パスワード変更 | 必要 |
| `children/` | GET, POST | 子アカウント一覧・作成 | 必要 |
| `children/{id}/` | GET, PATCH, DELETE | 子アカウント詳細・更新・削除 | 必要 |
| `my-qr/` | GET | 自分のQRコード取得 | 必要 |
| `regenerate-qr/` | POST | QRコード再発行 | 必要 |

---

## 3. students（生徒・保護者）- `/api/v1/students/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `/` | GET, POST | 生徒一覧・作成 | 必要 |
| `{id}/` | GET, PUT, DELETE | 生徒詳細・更新・削除 | 必要 |
| `{id}/qr-code/` | GET | 生徒QRコード取得 | 必要 |
| `{id}/regenerate-qr/` | POST | 生徒QRコード再発行 | 必要 |
| `guardians/` | GET, POST | 保護者一覧・作成 | 必要 |
| `guardians/{id}/` | GET, PUT, DELETE | 保護者詳細・更新・削除 | 必要 |
| `guardians/{id}/billing/` | GET | 保護者請求情報 | 必要 |
| `guardians/{id}/students/` | GET | 保護者の子供一覧 | 必要 |
| `suspension-requests/` | GET, POST | 休会申請一覧・作成 | 必要 |
| `withdrawal-requests/` | GET, POST | 退会申請一覧・作成 | 必要 |
| `bank-accounts/` | GET, POST | 銀行口座一覧・登録 | 必要 |
| `bank-account-requests/` | GET, POST | 口座変更申請一覧・作成 | 必要 |
| `friendship/` | GET, POST | 友達関係一覧・追加 | 必要 |

---

## 4. schools（学校・校舎）- `/api/v1/schools/`

### 管理者向け

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `brands/` | GET, POST | ブランド一覧・作成 | 必要 |
| `schools/` | GET, POST | 学校一覧・作成 | 必要 |
| `grades/` | GET, POST | 学年一覧・作成 | 必要 |
| `subjects/` | GET, POST | 教科一覧・作成 | 必要 |
| `classrooms/` | GET, POST | 教室一覧・作成 | 必要 |
| `time-slots/` | GET, POST | 時間帯一覧・作成 | 必要 |
| `schedules/` | GET, POST | スケジュール一覧・作成 | 必要 |
| `closures/` | GET, POST | 休業設定一覧・作成 | 必要 |
| `admin/calendar/` | GET, POST | 管理者カレンダー | 必要 |
| `admin/calendar/ab-swap/` | POST | A/Bクラス入替 | 必要 |
| `admin/google-calendar/` | GET, POST | Googleカレンダー連携 | 必要 |

### 公開API（認証不要）

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `public/schools/` | GET | 学校一覧 | 不要 |
| `public/prefectures/` | GET | 都道府県一覧 | 不要 |
| `public/areas/` | GET | エリア一覧 | 不要 |
| `public/brand-categories/` | GET | ブランドカテゴリ一覧 | 不要 |
| `public/trial-schedule/` | GET | 体験スケジュール | 不要 |
| `public/trial-booking/` | POST | 体験予約 | 不要 |
| `public/banks/` | GET | 銀行一覧 | 不要 |

---

## 5. lessons（授業・出欠）- `/api/v1/lessons/`

### 管理者向け

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `time-slots/` | GET, POST | 時間帯一覧・作成 | 必要 |
| `schedules/` | GET, POST | 授業スケジュール一覧・作成 | 必要 |
| `attendances/` | GET, POST | 出欠一覧・作成 | 必要 |
| `makeups/` | GET, POST | 振替授業一覧・作成 | 必要 |
| `records/` | GET, POST | 授業記録一覧・作成 | 必要 |
| `enrollments/` | GET, POST | グループ授業登録一覧・作成 | 必要 |

### 生徒・保護者向け

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `student-calendar/` | GET | 生徒カレンダー取得 | 必要 |
| `mark-absence/` | POST | 欠席登録 | 必要 |
| `absence-tickets/` | GET | 振替チケット一覧 | 必要 |
| `use-absence-ticket/` | POST | 振替予約 | 必要 |
| `transfer-available-classes/` | GET | 振替可能クラス取得 | 必要 |
| `cancel-absence/` | POST | 欠席キャンセル | 必要 |
| `cancel-makeup/` | POST | 振替キャンセル | 必要 |
| `qr-check-in/` | POST | QRコード出席 | 必要 |
| `qr-check-out/` | POST | QRコード退席 | 必要 |

### キオスク用（認証不要）

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `kiosk/schools/` | GET | キオスク用学校一覧 | 不要 |
| `kiosk/check-in/` | POST | キオスクチェックイン | 不要 |
| `kiosk/check-out/` | POST | キオスクチェックアウト | 不要 |

---

## 6. contracts（契約・コース）- `/api/v1/contracts/`

### 管理者向け

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `products/` | GET, POST | 商品一覧・作成 | 必要 |
| `discounts/` | GET, POST | 割引一覧・作成 | 必要 |
| `courses/` | GET, POST | コース一覧・作成 | 必要 |
| `packs/` | GET, POST | パック一覧・作成 | 必要 |
| `seminars/` | GET, POST | セミナー一覧・作成 | 必要 |
| `certifications/` | GET, POST | 認定資格一覧・作成 | 必要 |
| `student-items/` | GET, POST | 生徒商品一覧・登録 | 必要 |
| `contracts/` | GET, POST | 契約一覧・作成 | 必要 |

### 公開API（認証不要）

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `public/brands/` | GET | ブランド一覧 | 不要 |
| `public/courses/` | GET | コース一覧 | 不要 |
| `public/packs/` | GET | パック一覧 | 不要 |

---

## 7. billing（請求・入金）- `/api/v1/billing/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `invoices/` | GET, POST | 請求書一覧・作成 | 必要 |
| `invoices/{id}/invoice-pdf/` | GET | 請求書PDF出力 | 必要 |
| `payments/` | GET, POST | 入金一覧・登録 | 必要 |
| `payments/register/` | POST | 入金登録 | 必要 |
| `balances/` | GET | 預り金残高一覧 | 必要 |
| `refund-requests/` | GET, POST | 返金申請一覧・作成 | 必要 |
| `miles/` | GET, POST | マイル取引一覧・登録 | 必要 |
| `transfers/` | GET, POST | 銀行振込一覧・登録 | 必要 |
| `transfer-imports/` | GET, POST | 振込インポート一覧・実行 | 必要 |
| `confirmed/` | GET, POST | 確定請求一覧・登録 | 必要 |

---

## 8. pricing（料金計算）- `/api/v1/pricing/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `preview/` | POST | 料金プレビュー | 必要 |
| `confirm/` | POST | 購入確定 | 必要 |

---

## 9. hr（勤怠管理）- `/api/v1/hr/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `attendances/` | GET, POST | 勤怠記録一覧・作成 | 必要 |
| `attendances/today/` | GET | 今日の勤怠取得 | 必要 |
| `attendances/clock-in/` | POST | 出勤打刻 | 必要 |
| `attendances/clock-out/` | POST | 退勤打刻 | 必要 |
| `attendances/break-start/` | POST | 休憩開始 | 必要 |
| `attendances/break-end/` | POST | 休憩終了 | 必要 |
| `attendances/summary/` | GET | 月別勤怠サマリー | 必要 |

---

## 10. tasks（タスク管理）- `/api/v1/tasks/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `/` | GET, POST | タスク一覧・作成 | 必要 |
| `{id}/` | GET, PUT, DELETE | タスク詳細・更新・削除 | 必要 |
| `my-tasks/` | GET | 自分のタスク一覧 | 必要 |
| `pending/` | GET | 未完了タスク | 必要 |
| `today/` | GET | 今日のタスク | 必要 |
| `overdue/` | GET | 期限切れタスク | 必要 |
| `{id}/complete/` | POST | タスク完了 | 必要 |
| `{id}/reopen/` | POST | タスク再開 | 必要 |
| `{id}/approve-employee/` | POST | 社員登録承認 | 必要 |
| `{id}/reject-employee/` | POST | 社員登録却下 | 必要 |
| `categories/` | GET, POST | カテゴリ一覧・作成 | 必要 |
| `comments/` | GET, POST | コメント一覧・投稿 | 必要 |

---

## 11. tenants（テナント・社員）- `/api/v1/tenants/`

### 管理者向け

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `tenants/` | GET | テナント一覧 | 不要 |
| `positions/` | GET, POST | 役職一覧・作成 | 必要 |
| `permissions/` | GET, POST | 権限一覧・作成 | 必要 |
| `permissions/matrix/` | GET | 権限マトリックス | 必要 |
| `permissions/bulk-update/` | POST | 権限一括更新 | 必要 |
| `employees/` | GET, POST | 社員一覧・作成 | 必要 |
| `employees/grouped/` | GET | 校舎・ブランド別社員 | 必要 |
| `employees/pending/` | GET | 承認待ち社員 | 必要 |
| `employees/{id}/approve/` | POST | 社員承認 | 必要 |
| `employees/{id}/reject/` | POST | 社員却下 | 必要 |
| `employee-groups/` | GET, POST | 社員グループ一覧・作成 | 必要 |

### 公開API（認証不要）

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `departments/` | GET | 部署一覧 | 不要 |
| `roles/` | GET | 役割一覧 | 不要 |
| `positions/public/` | GET | 役職一覧（登録用） | 不要 |

---

## 12. communications（コミュニケーション）- `/api/v1/communications/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `channels/` | GET, POST | チャネル一覧・作成 | 必要 |
| `messages/` | GET, POST | メッセージ一覧・送信 | 必要 |
| `contact-logs/` | GET, POST | 連絡ログ一覧・登録 | 必要 |
| `notifications/` | GET, POST | 通知一覧・作成 | 必要 |
| `announcements/` | GET, POST | お知らせ一覧・作成 | 必要 |
| `feed/posts/` | GET, POST | フィード投稿一覧・投稿 | 必要 |
| `feed/comments/` | GET, POST | コメント一覧・投稿 | 必要 |
| `feed/bookmarks/` | GET, POST | ブックマーク一覧・追加 | 必要 |
| `bot/configs/` | GET, POST | ボット設定一覧・作成 | 必要 |
| `bot/faqs/` | GET, POST | ボットFAQ一覧・作成 | 必要 |

---

## 13. knowledge（ナレッジ）- `/api/v1/knowledge/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `manual-categories/` | GET, POST | マニュアルカテゴリ一覧・作成 | 必要 |
| `manuals/` | GET, POST | マニュアル一覧・作成 | 必要 |
| `manuals/pinned/` | GET | ピン留めマニュアル | 必要 |
| `manuals/recent/` | GET | 最近更新マニュアル | 必要 |
| `manuals/popular/` | GET | 人気マニュアル | 必要 |
| `template-categories/` | GET, POST | テンプレートカテゴリ一覧・作成 | 必要 |
| `templates/` | GET, POST | テンプレート一覧・作成 | 必要 |
| `templates/{id}/render/` | POST | テンプレートレンダリング | 必要 |
| `templates/popular/` | GET | よく使うテンプレート | 必要 |

---

## 14. core（システム）- `/api/v1/`

| エンドポイント | メソッド | 責務 | 認証 |
|---|---|---|---|
| `/` | GET | ヘルスチェック | 不要 |
| `/?detailed=true` | GET | 詳細ヘルスチェック | 不要 |
| `info/` | GET | システム情報 | 不要 |
| `upload/` | POST | ファイルアップロード | 必要 |
| `upload/multiple/` | POST | 複数ファイルアップロード | 必要 |

---

## エンドポイント統計

- **合計**: 約280エンドポイント
- **認証必要**: 約250
- **認証不要（公開API）**: 約30
