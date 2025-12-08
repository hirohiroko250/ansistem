/*
  # 新規登録フォーム更新に伴うスキーマ変更

  1. テーブル変更
    - `user_available_schools` テーブルを削除（通学可能校舎選択機能を削除）
    - `users` テーブルに `selected_area` カラムを追加（地域選択）
    - `user_brands` テーブルに `referral_source` カラムを追加（何で知ったか）

  2. セキュリティ
    - 既存のRLSポリシーは維持
    - user_available_schoolsテーブルの削除に伴い関連ポリシーも削除

  3. 重要な注意点
    - 通学可能校舎選択機能は削除され、地域選択→近隣校舎選択の2段階に変更
    - ブランド選択後に「何で知りましたか？」の情報を保存
*/

DROP TABLE IF EXISTS user_available_schools CASCADE;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'selected_area'
  ) THEN
    ALTER TABLE users ADD COLUMN selected_area text;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user_brands' AND column_name = 'referral_source'
  ) THEN
    ALTER TABLE user_brands ADD COLUMN referral_source text DEFAULT '';
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_users_selected_area ON users(selected_area);
