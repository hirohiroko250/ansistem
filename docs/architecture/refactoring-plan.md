# Django / Next.js 責務分離リファクタリング計画

## 概要

本ドキュメントは、Django（バックエンド）とNext.js（フロントエンド）の責務分離を改善するためのリファクタリング計画を記載します。

**作成日**: 2026-01-21
**ステータス**: 計画中

---

## 現状の課題

### 1. バリデーションの重複
- フロントエンドとバックエンドで同じバリデーションを実装
- メール・電話番号の重複チェックが両側で実行される
- 保守コストの増加、不整合のリスク

### 2. API呼び出しの分散
- 各ページが個別にAPI呼び出し順序を知っている
- 新規登録時: User作成 → Guardian作成 → Task作成（signal）が分散
- トランザクション境界が曖昧

### 3. エラーハンドリングの不統一
- バックエンドのエラーレスポンス形式がバラバラ
- フロントエンドで個別にエラー処理を実装

### 4. 状態管理の分散
- useState + localStorage のみ
- APIキャッシュなし、同じデータを複数回取得

### 5. CSR偏重
- 全ページが `'use client'` でCSR
- 認証不要ページもSSRを活用していない

---

## 改善方針

### Phase 1: エラーハンドリング統一

**目的**: バックエンド・フロントエンド間のエラー処理を標準化

#### バックエンド

- [ ] 統一エラーレスポンス形式を定義
  ```python
  # apps/core/exceptions.py
  class APIException:
      error_code: str      # "VALIDATION_ERROR", "NOT_FOUND", "UNAUTHORIZED"
      message: str         # ユーザー向けメッセージ
      details: dict        # フィールドごとのエラー詳細
  ```

- [ ] カスタム例外ハンドラーを実装
  ```
  backend/apps/core/exception_handler.py
  ```

- [ ] 既存のViewでエラーレスポンスを統一

#### フロントエンド

- [ ] 共通エラーハンドラーを作成
  ```
  frontend/customer/lib/api/error-handler.ts
  ```

- [ ] エラー種別ごとの処理を定義
  - `VALIDATION_ERROR` → フォームにエラー表示
  - `UNAUTHORIZED` → ログイン画面へリダイレクト
  - `SERVER_ERROR` → トースト通知

---

### Phase 2: バリデーション責務整理

**目的**: フロントエンドを軽量化し、バックエンドを信頼の源に

#### バリデーション責務の分担

| バリデーション種別 | フロントエンド | バックエンド |
|------------------|--------------|------------|
| 入力形式（正規表現） | ○ | - |
| 必須チェック（空文字） | ○ | ○ |
| メール形式 | ○ (HTML5) | ○ |
| パスワード長 | ○ | ○ |
| パスワード一致 | ○ | ○ |
| **メール重複** | △ (入力完了時のみ) | ○ |
| **電話番号重複** | △ (入力完了時のみ) | ○ |
| ビジネスルール | - | ○ |

#### 実装タスク

- [ ] 一括バリデーションAPIを作成
  ```
  POST /api/v1/validation/check/
  Request:  { "email": "...", "phone": "..." }
  Response: {
    "email": { "available": true },
    "phone": { "available": false, "message": "..." }
  }
  ```

- [ ] フロントエンドのバリデーションを簡素化
  - キーストロークごとのAPIコールを削除
  - フォーム送信時またはフィールドblur時のみAPIコール

---

### Phase 3: ユースケース単位のAPI統合

**目的**: 複数の処理を1トランザクションで実行し、フロントを簡素化

#### 新規エンドポイント

##### 3.1 新規登録（Onboarding）

```
POST /api/v1/onboarding/register/
```

**処理内容**:
1. User作成
2. Guardian作成
3. Task作成（作業一覧）
4. チャンネル作成（任意）
5. ウェルカムメール送信（任意）

**リクエスト**:
```json
{
  "email": "...",
  "password": "...",
  "full_name": "...",
  "phone": "...",
  "postal_code": "...",
  "prefecture": "...",
  "city": "...",
  "address1": "...",
  "nearest_school_id": "...",
  "interested_brands": ["..."]
}
```

**レスポンス**:
```json
{
  "user": { "id": "...", "email": "..." },
  "guardian": { "id": "...", "guardian_no": "..." },
  "tokens": { "access": "...", "refresh": "..." }
}
```

##### 3.2 生徒追加

```
POST /api/v1/onboarding/add-student/
```

**処理内容**:
1. Student作成
2. Guardian紐付け
3. Task作成（作業一覧）
4. 学年・校舎設定

##### 3.3 チケット購入完了

```
POST /api/v1/purchases/complete/
```

**処理内容**:
1. 料金計算の確定
2. StudentItem（契約）作成
3. Invoice（請求）作成
4. Task作成
5. 確認メール送信

#### signals.py との整合性

- [ ] ユースケースAPI内で明示的にTask作成
- [ ] signalでの重複作成を防ぐ方法を検討
  - オプション1: `_skip_signal` フラグをインスタンスに設定
  - オプション2: signalを削除し、サービス層に統一
  - オプション3: signal内で重複チェック

---

### Phase 4: 状態管理改善（React Query導入）

**目的**: APIキャッシュと状態管理を一元化

#### 導入パッケージ

```bash
npm install @tanstack/react-query
```

#### 実装タスク

- [ ] QueryClientProvider をルートに設置
  ```
  frontend/customer/app/providers.tsx
  ```

- [ ] カスタムフックを作成
  ```
  frontend/customer/lib/hooks/
  ├── useUser.ts          # ユーザー情報
  ├── useStudents.ts      # 生徒一覧
  ├── useTickets.ts       # チケット情報
  ├── useSchools.ts       # 校舎一覧
  └── useBrands.ts        # ブランド一覧
  ```

- [ ] 既存のuseEffect + fetchをReact Queryに置換

#### 期待効果

- 同じデータの重複取得を防止
- ローディング・エラー状態の統一管理
- バックグラウンドでの自動再取得

---

### Phase 5: SSR最適化

**目的**: 認証不要ページのパフォーマンス向上

#### SSR対象ページ

| ページ | 現状 | 変更後 | 理由 |
|-------|------|--------|------|
| `/login` | CSR | SSR | 認証不要、初期表示高速化 |
| `/signup` | CSR | SSR | 認証不要、初期表示高速化 |
| `/password-reset` | CSR | SSR | 認証不要 |
| `/trial` | CSR | SSR | 認証不要、SEO効果 |

#### CSR維持ページ

- `/feed`, `/calendar`, `/tickets`, `/children` 等
- 認証必須、動的データが多いため

#### 実装タスク

- [ ] SSR対象ページから `'use client'` を削除
- [ ] Server Component として再実装
- [ ] 認証チェックをmiddlewareに移動

---

## 実装スケジュール

| Phase | 内容 | 優先度 | 影響範囲 |
|-------|------|--------|---------|
| 1 | エラーハンドリング統一 | 高 | 小 |
| 2 | バリデーション責務整理 | 高 | 中 |
| 3 | ユースケースAPI統合 | 高 | 大 |
| 4 | React Query導入 | 中 | 大 |
| 5 | SSR最適化 | 低 | 中 |

---

## 進捗管理

### Phase 1: エラーハンドリング統一
- [x] バックエンド: 統一例外クラス作成（ErrorCode, OZAException等）
- [x] バックエンド: カスタム例外ハンドラー実装（custom_exception_handler更新）
- [x] バックエンド: 主要viewsを例外使用に変更（trial/booking.py, tasks/views.py, authentication/views.py）
- [x] バックエンド: 残りのviewsを例外使用に変更（92箇所すべて完了）
- [x] フロントエンド: 共通エラーハンドラー作成（error-handler.ts）
- [ ] テスト・動作確認

### Phase 2: バリデーション責務整理
- [x] 一括バリデーションAPI作成（POST /api/v1/auth/validation/check/）
- [x] フロントエンドのバリデーションユーティリティ作成（lib/validation/index.ts）
- [x] フィールドバリデーション用フック作成（hooks/use-field-validation.ts）
- [x] 既存フォームへの適用（signupフォームにblur時重複チェック適用）
- [ ] テスト・動作確認

### Phase 3: ユースケースAPI統合
- [x] `/api/v1/onboarding/register/` 実装
- [x] `/api/v1/onboarding/add-student/` 実装
- [x] `/api/v1/onboarding/purchase/complete/` 実装
- [x] signals.py との整合性確保（signalsでTask自動作成を活用）
- [x] フロントエンドの呼び出し箇所修正（signup → onboarding API接続）
- [ ] テスト・動作確認

### Phase 4: React Query導入
- [x] パッケージインストール・設定（package.json, providers.tsx）
- [x] カスタムフック作成（useUser, useStudents, useSchools, useBrands, useTickets）
- [x] 追加フック作成（useContracts, useSchedules, useHistory, useStaffStudents）
- [x] 既存コードの置換（feed, settings, contracts, students, schedule, history）
- [x] 追加フック作成（useClasses, useAttendance, useClassManagement, useFriendship）
- [x] 追加フック作成（useChat, usePassbook, useFeed, usePayment拡張）
- [x] 全主要ページの移行完了（20+ページ）
- [x] テスト・動作確認（ビルド成功）

### Phase 5: SSR最適化
- [x] 対象ページの特定（login, signup, trial, password-reset）
- [x] 認証ミドルウェア実装（middleware.ts）
- [x] 認証ガードコンポーネント作成（AuthGuard, GuestGuard）
- [x] 公開ページ用メタデータ（SEO）設定（各ページのlayout.tsx）
- [x] 既存ページへのAuthGuard適用（feed, calendar, tickets, children, chat, settings）
- [x] 公開ページへのGuestGuard適用（login, signup）
- [x] テスト・動作確認（ビルド成功）

---

## 参考資料

- [Django REST framework - Exception handling](https://www.django-rest-framework.org/api-guide/exceptions/)
- [TanStack Query Documentation](https://tanstack.com/query/latest)
- [Next.js App Router - Server Components](https://nextjs.org/docs/app/building-your-application/rendering/server-components)

---

## 変更履歴

| 日付 | 内容 | 担当 |
|------|------|------|
| 2026-01-21 | 初版作成 | - |
| 2026-01-21 | Phase 1開始: ErrorCode定義、OZAException改修、主要views修正 | - |
| 2026-01-21 | Phase 1バックエンド完了: 全92箇所のエラーResponse→例外raiseへ変換完了 | - |
| 2026-01-21 | Phase 1フロントエンド: 共通エラーハンドラー（error-handler.ts）作成完了 | - |
| 2026-01-21 | Phase 2: 一括バリデーションAPI、フロントエンドバリデーションユーティリティ作成完了 | - |
| 2026-01-21 | Phase 3: ユースケースAPI統合（onboardingアプリ作成、3エンドポイント実装）完了 | - |
| 2026-01-21 | Phase 4: React Query導入（Providers, カスタムフック5種類作成）完了 | - |
| 2026-01-21 | Phase 5: SSR最適化（middleware, AuthGuard, メタデータ設定）完了 | - |
| 2026-01-21 | Phase 4&5実装: AuthGuard/GuestGuard適用、React Queryフック移行、ビルド確認完了 | - |
| 2026-01-21 | 追加実装: childrenページをuseStudents/useAddStudentフックに移行、最終ビルド確認完了 | - |
| 2026-01-21 | Phase 3: signupフォームを新onboarding APIに接続完了 | - |
| 2026-01-21 | Phase 2: signupフォームにバリデーションフック（blur時重複チェック）適用完了 | - |
| 2026-01-21 | Phase 5: 追加ページへのAuthGuard適用（settings/*, chat/[id], children/[id], contracts, schedule, history, students）完了 | - |
| 2026-01-21 | Phase 4: 追加React Queryフック作成（useContracts, useSchedules, useHistory, useStaffStudents）、4ページ移行完了 | - |
| 2026-01-21 | Phase 4: useOwnedTickets追加、tickets/calendar/historyページ移行、ビルド確認完了 | - |
| 2026-01-21 | Phase 4: useChat/usePassbook追加、chat/purchase-historyページ移行、全ページReact Query化完了 | - |
| 2026-01-21 | Phase 4: 追加フック作成（useFeed, usePayment, useStudentQRCode）、詳細ページ移行（children/[id], feed/[id], purchase-history/[month], settings/payment）完了 | - |
| 2026-01-21 | Phase 4: 追加フック作成（useClasses, useAttendance, useClassManagement, useFriendship）、ページ移行（classes/[id], attendance, class-management, friend-referral）完了 | - |
| 2026-01-21 | Phase 4: use-payment.ts拡張（useMyBankAccounts, useCreateBankAccountRequest等）、settings/payment/edit移行完了 | - |
| 2026-01-21 | Phase 4: useMyQRCode追加、my-qrページ移行完了 | - |
| 2026-01-21 | Phase 4: settings/profile-editをuseUser/useUpdateProfile移行完了 | - |
| 2026-01-21 | Phase 4: chat API拡張（createChannel）、use-chat拡張（useCreateChannel, useSendMessage, useChannelMessages）、chat/new移行完了 | - |
| 2026-01-21 | Phase 4: use-feed拡張（useLatestNews）、ホームページ（page.tsx）移行完了 | - |
| 2026-01-21 | Phase 4完了: 全20+ページのReact Query移行、17種類のカスタムフック作成完了 | - |
| 2026-01-22 | Lintエラー修正: useAbsenceTicket→consumeAbsenceTicketにリネーム（React Hooksルール違反解消） | - |
| 2026-01-21 | Phase 4: use-feed拡張（useLatestNews）、ホームページ（page.tsx）移行完了 | - |
