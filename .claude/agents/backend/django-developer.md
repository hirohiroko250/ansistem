# Django Developer

Django/DRFのバックエンド開発エージェント。

## 技術スタック
- Django 4.x
- Django REST Framework
- PostgreSQL
- Redis (キャッシュ)

## プロジェクト構造
```
backend/
├── apps/
│   ├── core/        # 共通機能
│   ├── users/       # ユーザー管理
│   ├── students/    # 生徒・保護者管理
│   ├── schools/     # 校舎・ブランド管理
│   ├── lessons/     # 授業・予約管理
│   ├── contracts/   # 契約・チケット管理
│   ├── hr/          # 勤怠管理
│   └── tasks/       # タスク管理
└── config/          # Django設定
```

## 使用方法
```
[機能]のAPIを作成して
[モデル]にフィールドを追加して
```

## コーディング規約
- ViewSetはModelViewSetを継承
- シリアライザは用途別に分離（List/Detail/Create/Update）
- テナント分離は`tenant_id`フィールドで実現
- 論理削除は`deleted_at`フィールドを使用
