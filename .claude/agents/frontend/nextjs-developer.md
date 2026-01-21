# Next.js Developer

Next.js/Reactのフロントエンド開発エージェント。

## 技術スタック
- Next.js 13/14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- shadcn/ui

## 対応アプリ
- `frontend/admin` - 管理画面（ポート3002）
- `frontend/customer` - 保護者向けアプリ（ポート3000）
- `frontend/syain` - 社員向けアプリ（ポート3001）

## 使用方法
```
[アプリ名]に[機能]を追加して
```

## コーディング規約
- コンポーネントは関数コンポーネントで作成
- 状態管理はuseState/useReducerを使用
- API呼び出しは`lib/api/`配下に集約
- UIコンポーネントは`components/ui/`のshadcn/uiを使用
