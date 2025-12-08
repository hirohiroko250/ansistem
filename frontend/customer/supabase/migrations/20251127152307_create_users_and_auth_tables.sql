/*
  # ユーザー認証テーブルの作成

  1. 新しいテーブル
    - `users`
      - `id` (uuid, primary key) - ユーザーID
      - `phone` (text, unique) - 電話番号
      - `email` (text, unique) - メールアドレス
      - `password_hash` (text) - ハッシュ化されたパスワード
      - `last_name` (text) - 姓
      - `first_name` (text) - 名
      - `last_name_kana` (text) - セイ
      - `first_name_kana` (text) - メイ
      - `nearest_school_id` (text) - 最寄り校舎ID
      - `created_at` (timestamptz) - 作成日時
      - `updated_at` (timestamptz) - 更新日時

    - `user_available_schools`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key) - ユーザーID
      - `school_id` (text) - 通学可能校舎ID
      - `created_at` (timestamptz) - 作成日時

    - `user_brands`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key) - ユーザーID
      - `brand_id` (text) - ブランドID
      - `expectations` (text) - 期待すること
      - `created_at` (timestamptz) - 作成日時

  2. セキュリティ
    - すべてのテーブルでRLSを有効化
    - 認証済みユーザーは自分のデータのみ読み書き可能
*/

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  phone text UNIQUE NOT NULL,
  email text UNIQUE NOT NULL,
  password_hash text NOT NULL,
  last_name text NOT NULL,
  first_name text NOT NULL,
  last_name_kana text NOT NULL,
  first_name_kana text NOT NULL,
  nearest_school_id text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_available_schools (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  school_id text NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(user_id, school_id)
);

CREATE TABLE IF NOT EXISTS user_brands (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand_id text NOT NULL,
  expectations text DEFAULT '',
  created_at timestamptz DEFAULT now(),
  UNIQUE(user_id, brand_id)
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_available_schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_brands ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON users FOR SELECT
  TO authenticated
  USING (id = (current_setting('app.current_user_id', true))::uuid);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  TO authenticated
  USING (id = (current_setting('app.current_user_id', true))::uuid)
  WITH CHECK (id = (current_setting('app.current_user_id', true))::uuid);

CREATE POLICY "Users can view own available schools"
  ON user_available_schools FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id', true))::uuid);

CREATE POLICY "Users can insert own available schools"
  ON user_available_schools FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id', true))::uuid);

CREATE POLICY "Users can delete own available schools"
  ON user_available_schools FOR DELETE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id', true))::uuid);

CREATE POLICY "Users can view own brands"
  ON user_brands FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id', true))::uuid);

CREATE POLICY "Users can insert own brands"
  ON user_brands FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id', true))::uuid);

CREATE POLICY "Users can update own brands"
  ON user_brands FOR UPDATE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id', true))::uuid)
  WITH CHECK (user_id = (current_setting('app.current_user_id', true))::uuid);

CREATE POLICY "Users can delete own brands"
  ON user_brands FOR DELETE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id', true))::uuid);

CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_available_schools_user_id ON user_available_schools(user_id);
CREATE INDEX IF NOT EXISTS idx_user_brands_user_id ON user_brands(user_id);
