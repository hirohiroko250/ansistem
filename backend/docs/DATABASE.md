# OZA System データベース設計書

## 概要

OZA Systemは塾管理システムのバックエンドです。マルチテナント対応のSaaSアーキテクチャを採用しています。

### テーブル数
| アプリ | モデル数 | 説明 |
|--------|---------|------|
| tenants | 1 | テナント管理 |
| users | 1 | ユーザー認証・アカウント |
| schools | 5 | 校舎・学年・教科マスタ |
| students | 4 | 生徒・保護者管理 |
| contracts | 7 | 契約・商品・料金管理 |
| lessons | 6 | 授業・出席・振替管理 |
| hr | 8 | スタッフ・勤怠・給与管理 |
| communications | 15 | チャット・通知・フィード |
| **合計** | **47** | |

---

## ER図（概念）

```
┌─────────────────────────────────────────────────────────────────────┐
│                            TENANT                                    │
│                         (テナント)                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│     USER      │         │    SCHOOL     │         │   PRODUCT     │
│  (ユーザー)   │         │    (校舎)     │         │    (商品)     │
└───────────────┘         └───────────────┘         └───────────────┘
        │                         │                           │
        │    ┌────────────────────┼────────────────────┐      │
        │    │                    │                    │      │
        ▼    ▼                    ▼                    ▼      ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│   STUDENT     │◄────────│   CONTRACT    │────────►│    PRICE      │
│    (生徒)     │         │    (契約)     │         │    (価格)     │
└───────────────┘         └───────────────┘         └───────────────┘
        │                         │
        │                         │
        ▼                         ▼
┌───────────────┐         ┌───────────────┐
│   GUARDIAN    │         │   SCHEDULE    │
│   (保護者)    │         │ (授業スケジュール) │
└───────────────┘         └───────────────┘
```

---

## 1. テナント管理 (tenants)

### tenants - テナント
塾運営会社（契約企業）の情報を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_code | VARCHAR(20) | テナントコード（一意） |
| tenant_name | VARCHAR(100) | テナント名 |
| contact_email | VARCHAR | 連絡先メール |
| contact_phone | VARCHAR | 連絡先電話番号 |
| plan_type | VARCHAR | プラン種別（FREE/STANDARD/PROFESSIONAL/ENTERPRISE） |
| max_schools | INT | 最大校舎数 |
| max_users | INT | 最大ユーザー数 |
| settings | JSON | テナント設定 |
| features | JSON | 有効な機能フラグ |
| is_active | BOOL | 有効フラグ |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

---

## 2. ユーザー管理 (users)

### t16_users - ユーザー
ログインアカウントを管理します。生徒・保護者・講師・スタッフ・管理者すべてのアカウント。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| email | VARCHAR | メールアドレス（一意） |
| password | VARCHAR | パスワード（ハッシュ） |
| user_type | VARCHAR | ユーザー種別（STUDENT/GUARDIAN/TEACHER/STAFF/ADMIN） |
| role | VARCHAR | ロール（USER/TEACHER/SCHOOL_MANAGER/ADMIN/SUPER_ADMIN） |
| last_name | VARCHAR(50) | 姓 |
| first_name | VARCHAR(50) | 名 |
| last_name_kana | VARCHAR(50) | 姓（カナ） |
| first_name_kana | VARCHAR(50) | 名（カナ） |
| display_name | VARCHAR(100) | 表示名 |
| phone | VARCHAR(20) | 電話番号 |
| **parent_user_id** | UUID | **親アカウントID（階層構造用）** |
| student_id | UUID | 紐づく生徒ID |
| staff_id | UUID | 紐づくスタッフID |
| primary_school_id | UUID | 主所属校舎ID |
| is_active | BOOL | 有効フラグ |
| is_email_verified | BOOL | メール認証済み |
| last_login_at | TIMESTAMP | 最終ログイン日時 |
| created_at | TIMESTAMP | 作成日時 |

#### 階層構造
```
保護者アカウント (user_type=GUARDIAN)
   ├── 生徒A (user_type=STUDENT, parent_user_id=保護者ID)
   └── 生徒B (user_type=STUDENT, parent_user_id=保護者ID)
```

---

## 3. 校舎管理 (schools)

### t17_brands - ブランド
教室ブランド（個別指導/集団授業など）を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| brand_code | VARCHAR(20) | ブランドコード |
| brand_name | VARCHAR(100) | ブランド名 |
| brand_type | VARCHAR | ブランド種別 |
| color_primary | VARCHAR(7) | テーマカラー（#RRGGBB） |
| is_active | BOOL | 有効フラグ |

### t18_schools - 校舎
教室・校舎の情報を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| brand_id | UUID | ブランドID（FK） |
| school_code | VARCHAR(20) | 校舎コード |
| school_name | VARCHAR(100) | 校舎名 |
| postal_code | VARCHAR(8) | 郵便番号 |
| prefecture | VARCHAR(10) | 都道府県 |
| city | VARCHAR(50) | 市区町村 |
| address1 | VARCHAR(100) | 住所1 |
| phone | VARCHAR(20) | 電話番号 |
| capacity | INT | 定員 |
| is_active | BOOL | 有効フラグ |

### t31_grades - 学年
学年マスタを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| grade_code | VARCHAR(10) | 学年コード |
| grade_name | VARCHAR(50) | 学年名（例：小学1年） |
| category | VARCHAR | カテゴリ（elementary/junior_high/high_school） |
| school_year | INT | 学年（1〜12） |
| sort_order | INT | 表示順 |
| is_active | BOOL | 有効フラグ |

### t32_subjects - 教科
教科マスタを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| subject_code | VARCHAR(20) | 教科コード |
| subject_name | VARCHAR(50) | 教科名 |
| category | VARCHAR | カテゴリ（main/sub/special） |
| color | VARCHAR(7) | テーマカラー（#RRGGBB） |
| is_active | BOOL | 有効フラグ |

### t18_classrooms - 教室
各校舎の教室を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| school_id | UUID | 校舎ID（FK） |
| classroom_code | VARCHAR(20) | 教室コード |
| classroom_name | VARCHAR(50) | 教室名 |
| capacity | INT | 定員 |
| equipment | JSON | 設備（プロジェクター等） |
| is_active | BOOL | 有効フラグ |

---

## 4. 生徒・保護者管理 (students)

### t01_students - 生徒
生徒の基本情報を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| student_no | VARCHAR(20) | 生徒番号 |
| last_name | VARCHAR(50) | 姓 |
| first_name | VARCHAR(50) | 名 |
| last_name_kana | VARCHAR(50) | 姓（カナ） |
| first_name_kana | VARCHAR(50) | 名（カナ） |
| email | VARCHAR | メールアドレス |
| phone | VARCHAR(20) | 電話番号 |
| birth_date | DATE | 生年月日 |
| gender | VARCHAR | 性別（male/female/other） |
| school_name | VARCHAR(100) | 在籍学校名 |
| grade_id | UUID | 学年ID（FK） |
| primary_school_id | UUID | 主所属校舎ID（FK） |
| user_id | UUID | ユーザーアカウントID（FK） |
| status | VARCHAR | ステータス（active/resting/withdrawn/graduated） |
| enrollment_date | DATE | 入塾日 |
| withdrawal_date | DATE | 退塾日 |
| tags | JSON | タグ |
| custom_fields | JSON | カスタムフィールド |

### t02_guardians - 保護者
保護者の基本情報を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| guardian_no | VARCHAR(20) | 保護者番号 |
| last_name | VARCHAR(50) | 姓 |
| first_name | VARCHAR(50) | 名 |
| email | VARCHAR | メールアドレス |
| phone | VARCHAR(20) | 電話番号 |
| phone_mobile | VARCHAR(20) | 携帯電話 |
| postal_code | VARCHAR(8) | 郵便番号 |
| prefecture | VARCHAR(10) | 都道府県 |
| city | VARCHAR(50) | 市区町村 |
| address1 | VARCHAR(100) | 住所1 |
| user_id | UUID | ユーザーアカウントID（FK） |

### t10_student_schools - 生徒所属
生徒と校舎の紐付け（在籍履歴）を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| student_id | UUID | 生徒ID（FK） |
| school_id | UUID | 校舎ID（FK） |
| brand_id | UUID | ブランドID（FK） |
| enrollment_status | VARCHAR | 在籍状況（active/transferred/ended） |
| start_date | DATE | 開始日 |
| end_date | DATE | 終了日 |
| is_primary | BOOL | 主所属フラグ |

### t11_student_guardians - 生徒保護者関連
生徒と保護者の紐付けを管理します。1人の生徒に複数の保護者、1人の保護者に複数の生徒（兄弟）を紐付けられます。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| student_id | UUID | 生徒ID（FK） |
| guardian_id | UUID | 保護者ID（FK） |
| relationship | VARCHAR | 続柄（father/mother/grandfather/grandmother/other） |
| is_primary | BOOL | 主保護者フラグ |
| is_emergency_contact | BOOL | 緊急連絡先フラグ |
| is_billing_target | BOOL | 請求先フラグ |
| contact_priority | INT | 連絡優先順位 |

---

## 5. 契約・商品管理 (contracts)

### t05_products - 商品
販売する商品（コース・教材等）を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| product_code | VARCHAR(20) | 商品コード |
| product_name | VARCHAR(100) | 商品名 |
| product_type | VARCHAR | 商品種別（regular/seasonal/material/facility） |
| billing_type | VARCHAR | 課金種別（monthly/one_time/per_lesson） |
| brand_id | UUID | ブランドID（FK） |
| subject_id | UUID | 教科ID（FK） |
| base_price | DECIMAL | 基本価格 |
| tax_rate | DECIMAL | 税率 |
| is_active | BOOL | 有効フラグ |

### t06_prices - 価格
学年別・校舎別の価格を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| product_id | UUID | 商品ID（FK） |
| grade_id | UUID | 学年ID（FK、NULL=全学年） |
| school_id | UUID | 校舎ID（FK、NULL=全校舎） |
| price | DECIMAL | 価格 |
| valid_from | DATE | 有効開始日 |
| valid_until | DATE | 有効終了日 |

### t07_discounts - 割引
割引マスタを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| discount_code | VARCHAR(20) | 割引コード |
| discount_name | VARCHAR(100) | 割引名 |
| discount_type | VARCHAR | 割引種別（sibling/multi_subject/campaign） |
| calculation_type | VARCHAR | 計算方法（percentage/fixed） |
| value | DECIMAL | 割引値（%または金額） |
| is_active | BOOL | 有効フラグ |

### t03_contracts - 契約
生徒との契約を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| contract_no | VARCHAR(30) | 契約番号 |
| student_id | UUID | 生徒ID（FK） |
| guardian_id | UUID | 保護者ID（FK） |
| school_id | UUID | 校舎ID（FK） |
| contract_date | DATE | 契約日 |
| start_date | DATE | 開始日 |
| end_date | DATE | 終了日 |
| status | VARCHAR | ステータス（draft/active/suspended/terminated） |
| monthly_total | DECIMAL | 月額合計 |
| discount_total | DECIMAL | 割引合計 |

### t04_contract_details - 契約詳細
契約に含まれる商品明細を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| contract_id | UUID | 契約ID（FK） |
| product_id | UUID | 商品ID（FK） |
| subject_id | UUID | 教科ID（FK） |
| quantity | INT | 数量 |
| unit_price | DECIMAL | 単価 |
| subtotal | DECIMAL | 小計 |
| discount_amount | DECIMAL | 割引額 |
| total | DECIMAL | 合計 |
| lessons_per_week | INT | 週あたり授業数 |

### t51_seasonal_enrollments - 講習申込
季節講習の申込を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| enrollment_no | VARCHAR(30) | 申込番号 |
| student_id | UUID | 生徒ID（FK） |
| school_id | UUID | 校舎ID（FK） |
| season_type | VARCHAR | 季節（spring/summer/autumn/winter） |
| year | INT | 年度 |
| status | VARCHAR | ステータス |
| total | DECIMAL | 合計金額 |

---

## 6. 授業管理 (lessons)

### t15_time_slots - 時間枠
授業の時間枠マスタを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| slot_code | VARCHAR(10) | 時間枠コード |
| slot_name | VARCHAR(50) | 時間枠名（例：1限） |
| start_time | TIME | 開始時刻 |
| end_time | TIME | 終了時刻 |
| duration_minutes | INT | 時間（分） |
| school_id | UUID | 校舎ID（FK、NULL=全校舎共通） |
| day_of_week | INT | 曜日（0=日〜6=土、NULL=全曜日） |
| is_active | BOOL | 有効フラグ |

### t13_lesson_schedules - 授業スケジュール
授業の予定を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| school_id | UUID | 校舎ID（FK） |
| classroom_id | UUID | 教室ID（FK） |
| subject_id | UUID | 教科ID（FK） |
| lesson_type | VARCHAR | 授業種別（individual/group/online） |
| date | DATE | 授業日 |
| time_slot_id | UUID | 時間枠ID（FK） |
| start_time | TIME | 開始時刻 |
| end_time | TIME | 終了時刻 |
| teacher_id | UUID | 講師ID（FK） |
| student_id | UUID | 生徒ID（FK、個別指導の場合） |
| contract_id | UUID | 契約ID（FK） |
| status | VARCHAR | ステータス（scheduled/completed/cancelled） |

### t14_lesson_records - 授業実績
実施した授業の記録を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| schedule_id | UUID | スケジュールID（FK） |
| actual_start_time | TIME | 実際の開始時刻 |
| actual_end_time | TIME | 実際の終了時刻 |
| content | TEXT | 授業内容 |
| homework | TEXT | 宿題 |
| understanding_level | VARCHAR | 理解度（excellent/good/average/poor） |
| teacher_comment | TEXT | 講師コメント |

### t19_attendances - 出席記録
生徒の出席を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| schedule_id | UUID | スケジュールID（FK） |
| student_id | UUID | 生徒ID（FK） |
| status | VARCHAR | 出席状況（present/absent/late/makeup） |
| check_in_time | TIME | 入室時刻 |
| check_out_time | TIME | 退室時刻 |
| absence_reason | TEXT | 欠席理由 |

### t20_makeup_lessons - 振替管理
振替授業を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| original_schedule_id | UUID | 元の授業ID（FK） |
| student_id | UUID | 生徒ID（FK） |
| makeup_schedule_id | UUID | 振替先授業ID（FK） |
| status | VARCHAR | ステータス（requested/approved/completed/rejected） |
| valid_until | DATE | 振替期限 |
| requested_at | TIMESTAMP | 申請日時 |
| processed_at | TIMESTAMP | 処理日時 |

---

## 7. 人事・勤怠管理 (hr)

### t28_staff - スタッフ
講師・スタッフの情報を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| staff_no | VARCHAR(20) | スタッフ番号 |
| last_name | VARCHAR(50) | 姓 |
| first_name | VARCHAR(50) | 名 |
| email | VARCHAR | メールアドレス |
| phone | VARCHAR(20) | 電話番号 |
| staff_type | VARCHAR | 雇用形態（full_time/part_time/contract） |
| position | VARCHAR | 役職（teacher/manager/admin） |
| hire_date | DATE | 入社日 |
| status | VARCHAR | ステータス（active/on_leave/retired） |
| primary_school_id | UUID | 主所属校舎ID（FK） |
| user_id | UUID | ユーザーアカウントID（FK） |
| bank_name | VARCHAR | 銀行名 |
| bank_account_number | VARCHAR | 口座番号 |

### t28_staff_schools - スタッフ所属校舎
スタッフと校舎の紐付けを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| staff_id | UUID | スタッフID（FK） |
| school_id | UUID | 校舎ID（FK） |
| is_primary | BOOL | 主所属フラグ |
| start_date | DATE | 開始日 |
| end_date | DATE | 終了日 |

### t41_shifts - シフト
スタッフのシフトを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| staff_id | UUID | スタッフID（FK） |
| school_id | UUID | 校舎ID（FK） |
| date | DATE | 日付 |
| start_time | TIME | 開始時刻 |
| end_time | TIME | 終了時刻 |
| break_minutes | INT | 休憩時間（分） |
| status | VARCHAR | ステータス（draft/approved/rejected） |

### t40_attendances - 勤怠記録
スタッフの勤怠を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| staff_id | UUID | スタッフID（FK） |
| school_id | UUID | 校舎ID（FK） |
| date | DATE | 日付 |
| attendance_type | VARCHAR | 勤怠種別（normal/paid_leave/sick_leave） |
| clock_in | TIME | 出勤時刻 |
| clock_out | TIME | 退勤時刻 |
| work_minutes | INT | 勤務時間（分） |
| overtime_minutes | INT | 残業時間（分） |
| lesson_count | INT | 授業コマ数 |
| is_approved | BOOL | 承認済みフラグ |

### t46_salary_masters - 給与マスタ
スタッフの給与設定を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| staff_id | UUID | スタッフID（FK） |
| salary_type | VARCHAR | 給与種別（hourly/per_lesson/monthly） |
| base_hourly_rate | DECIMAL | 時給 |
| base_lesson_rate | DECIMAL | コマ給 |
| base_monthly_salary | DECIMAL | 月給 |
| transportation_allowance | DECIMAL | 交通費 |
| valid_from | DATE | 有効開始日 |

### t47_payrolls - 給与明細
月次の給与明細を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| staff_id | UUID | スタッフID（FK） |
| year | INT | 年 |
| month | INT | 月 |
| payment_date | DATE | 支給日 |
| work_days | INT | 出勤日数 |
| work_hours | DECIMAL | 勤務時間 |
| lesson_count | INT | 授業コマ数 |
| gross_salary | DECIMAL | 総支給額 |
| total_deductions | DECIMAL | 控除合計 |
| net_salary | DECIMAL | 手取り |
| status | VARCHAR | ステータス（draft/approved/paid） |

---

## 8. コミュニケーション (communications)

### communication_channels - チャンネル
チャットルームを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| channel_type | VARCHAR | 種別（INTERNAL/EXTERNAL/SUPPORT/BOT） |
| name | VARCHAR(100) | チャンネル名 |
| student_id | UUID | 生徒ID（FK） |
| guardian_id | UUID | 保護者ID（FK） |
| school_id | UUID | 校舎ID（FK） |
| is_archived | BOOL | アーカイブフラグ |

### communication_messages - メッセージ
チャットメッセージを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| channel_id | UUID | チャンネルID（FK） |
| message_type | VARCHAR | 種別（TEXT/IMAGE/FILE/BOT） |
| sender_id | UUID | 送信者ID（FK） |
| content | TEXT | 内容 |
| attachment_url | VARCHAR | 添付ファイルURL |
| reply_to_id | UUID | 返信先メッセージID（FK） |
| is_deleted | BOOL | 削除フラグ |
| created_at | TIMESTAMP | 作成日時 |

### communication_contact_logs - 対応履歴
顧客対応の履歴（CRM）を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| student_id | UUID | 生徒ID（FK） |
| guardian_id | UUID | 保護者ID（FK） |
| contact_type | VARCHAR | 対応種別（PHONE_IN/EMAIL/VISIT/MEETING） |
| subject | VARCHAR(200) | 件名 |
| content | TEXT | 内容 |
| handled_by_id | UUID | 対応者ID（FK） |
| priority | VARCHAR | 優先度（LOW/MEDIUM/HIGH/URGENT） |
| status | VARCHAR | ステータス（OPEN/RESOLVED/CLOSED） |

### communication_notifications - 通知
プッシュ通知・アプリ内通知を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| notification_type | VARCHAR | 種別（MESSAGE/LESSON_REMINDER/MAKEUP_APPROVED） |
| user_id | UUID | 宛先ユーザーID（FK） |
| title | VARCHAR(200) | タイトル |
| content | TEXT | 内容 |
| is_read | BOOL | 既読フラグ |
| created_at | TIMESTAMP | 作成日時 |

### communication_bot_configs - ボット設定
チャットボットの設定を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| name | VARCHAR(50) | ボット名 |
| bot_type | VARCHAR | 種別（FAQ/SCHEDULE/GENERAL） |
| welcome_message | TEXT | ウェルカムメッセージ |
| fallback_message | TEXT | フォールバックメッセージ |
| ai_enabled | BOOL | AI応答有効フラグ |
| is_active | BOOL | 有効フラグ |

### communication_bot_faqs - ボットFAQ
ボットのFAQを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| bot_config_id | UUID | ボット設定ID（FK） |
| category | VARCHAR | カテゴリ |
| question | TEXT | 質問 |
| keywords | JSON | キーワード（マッチング用） |
| answer | TEXT | 回答 |
| next_action | VARCHAR | 次のアクション |
| is_active | BOOL | 有効フラグ |

### communication_feed_posts - フィード投稿
Instagram風のフィード投稿を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| tenant_id | UUID | テナントID |
| post_type | VARCHAR | 種別（TEXT/IMAGE/VIDEO/GALLERY） |
| author_id | UUID | 投稿者ID（FK） |
| school_id | UUID | 校舎ID（FK） |
| content | TEXT | 本文 |
| visibility | VARCHAR | 公開範囲（PUBLIC/SCHOOL/GRADE/STAFF） |
| hashtags | JSON | ハッシュタグ |
| is_pinned | BOOL | 固定表示フラグ |
| allow_comments | BOOL | コメント許可 |
| allow_likes | BOOL | いいね許可 |
| like_count | INT | いいね数 |
| comment_count | INT | コメント数 |
| view_count | INT | 閲覧数 |
| is_published | BOOL | 公開フラグ |
| created_at | TIMESTAMP | 作成日時 |

### communication_feed_media - フィードメディア
フィード投稿の画像・動画を管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| post_id | UUID | 投稿ID（FK） |
| media_type | VARCHAR | 種別（IMAGE/VIDEO） |
| file_url | VARCHAR | ファイルURL |
| thumbnail_url | VARCHAR | サムネイルURL |
| sort_order | INT | 表示順 |

### communication_feed_comments - フィードコメント
フィード投稿へのコメントを管理します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | 主キー |
| post_id | UUID | 投稿ID（FK） |
| user_id | UUID | コメント者ID（FK） |
| content | TEXT | コメント内容 |
| parent_id | UUID | 返信先コメントID（FK） |
| like_count | INT | いいね数 |
| is_deleted | BOOL | 削除フラグ |
| created_at | TIMESTAMP | 作成日時 |

---

## インデックス設計

### 主要なインデックス

```sql
-- テナントIDでの絞り込み（全テーブル共通）
CREATE INDEX idx_{table}_tenant ON {table}(tenant_id);

-- 生徒検索
CREATE INDEX idx_students_tenant_status ON t01_students(tenant_id, status);
CREATE INDEX idx_students_school ON t01_students(primary_school_id);

-- 授業スケジュール
CREATE INDEX idx_schedules_tenant_date ON t13_lesson_schedules(tenant_id, date);
CREATE INDEX idx_schedules_teacher_date ON t13_lesson_schedules(teacher_id, date);
CREATE INDEX idx_schedules_student_date ON t13_lesson_schedules(student_id, date);

-- メッセージ
CREATE INDEX idx_messages_channel_created ON communication_messages(channel_id, created_at);

-- 通知
CREATE INDEX idx_notifications_user_read ON communication_notifications(user_id, is_read);
```

---

## マイグレーション

```bash
# マイグレーションファイル作成
python manage.py makemigrations

# マイグレーション適用
python manage.py migrate

# マスターデータ投入
python manage.py loaddata initial_data
```
