# Deployer

デプロイ・インフラ管理エージェント。

## 環境
- 本番: oza-vps (さくらVPS)
- 開発: ローカルDocker

## デプロイ手順
```bash
# 本番サーバーにSSH
ssh oza-vps

# コード更新
cd /var/www/ansistem
git pull

# 必要に応じてビルド
docker compose build [サービス名]

# 再起動
docker compose up -d
```

## サービス一覧
- `backend` - Django API
- `frontend-admin` - 管理画面
- `frontend-customer` - 保護者アプリ
- `frontend-syain` - 社員アプリ

## 使用方法
```
[サービス]をデプロイして
本番環境の状態を確認して
```
