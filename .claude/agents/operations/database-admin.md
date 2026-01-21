# Database Admin

データベース管理エージェント。

## データベース
- PostgreSQL 15
- コンテナ名: oza_db

## 役割
- マイグレーション管理
- データ整合性チェック
- パフォーマンスチューニング
- バックアップ・リストア

## よく使うコマンド
```bash
# マイグレーション作成
docker compose exec backend python manage.py makemigrations [app_name]

# マイグレーション実行
docker compose exec backend python manage.py migrate

# DBシェル
docker compose exec backend python manage.py dbshell
```

## 使用方法
```
[モデル]のマイグレーションを作成して
データベースの状態を確認して
```
