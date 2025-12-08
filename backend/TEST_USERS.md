# テストユーザー情報

## 保護者ユーザー（子供あり）

| メールアドレス | パスワード | 保護者名 | 子供数 | Tenant |
|---|---|---|---|---|
| katsuno.h@meidaisky.jp | 1111 | 勝野 紘尚 | 1人 | OZA SYSTEM |
| oza@test.com | 1111 | 尾崎 テスト | 1人 | OZA SYSTEM |

## その他ユーザー

| メールアドレス | パスワード | 備考 |
|---|---|---|
| admin@test.com | admin123 | 管理者（スーパーユーザー） |
| parent@test.com | - | 保護者なし |
| test456@example.com | - | テスト用 |

## 注意事項

- パスワードが `-` のユーザーは未設定または不明
- 保護者ユーザーでログインすると `/children` ページで子供一覧が表示される
- 保護者プロファイルがないユーザーは子供が表示されない

## パスワード変更方法

```bash
source venv/bin/activate
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(email='メールアドレス')
user.set_password('新しいパスワード')
user.save()
"
```

## ユーザー情報確認コマンド

```bash
source venv/bin/activate
python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.students.models import Guardian, Student
User = get_user_model()

for u in User.objects.all():
    guardian = getattr(u, 'guardian_profile', None)
    student_count = Student.objects.filter(guardian=guardian).count() if guardian else 0
    print(f'{u.email}: Guardian={guardian.full_name if guardian else \"なし\"}, Students={student_count}人')
"
```
