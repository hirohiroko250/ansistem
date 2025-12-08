/*
  # Create Posts System (Instagram-style Feed)

  1. New Tables
    - `posts`
      - `id` (uuid, primary key)
      - `instructor_id` (uuid, foreign key to profiles)
      - `campus_id` (uuid, foreign key to campuses)
      - `content` (text) - Post content/caption
      - `image_url` (text, nullable) - Image URL
      - `video_url` (text, nullable) - Video URL
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)
    
    - `post_reactions`
      - `id` (uuid, primary key)
      - `post_id` (uuid, foreign key to posts)
      - `user_id` (uuid, foreign key to profiles)
      - `reaction_type` (text) - e.g., 'like', 'heart', 'clap', 'fire'
      - `created_at` (timestamptz)
      - Unique constraint on (post_id, user_id, reaction_type)
    
    - `post_comments`
      - `id` (uuid, primary key)
      - `post_id` (uuid, foreign key to posts)
      - `user_id` (uuid, foreign key to profiles)
      - `content` (text)
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on all tables
    - Authenticated users can view all posts
    - Users can create their own posts
    - Users can update/delete their own posts
    - Users can add reactions and comments
    - Users can delete their own reactions and comments
*/

-- Create posts table
CREATE TABLE IF NOT EXISTS posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instructor_id uuid REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  campus_id uuid REFERENCES campuses(id) ON DELETE SET NULL,
  content text NOT NULL,
  image_url text,
  video_url text,
  created_at timestamptz DEFAULT now() NOT NULL,
  updated_at timestamptz DEFAULT now() NOT NULL
);

-- Create post_reactions table
CREATE TABLE IF NOT EXISTS post_reactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid REFERENCES posts(id) ON DELETE CASCADE NOT NULL,
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  reaction_type text NOT NULL DEFAULT 'like',
  created_at timestamptz DEFAULT now() NOT NULL,
  UNIQUE(post_id, user_id, reaction_type)
);

-- Create post_comments table
CREATE TABLE IF NOT EXISTS post_comments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid REFERENCES posts(id) ON DELETE CASCADE NOT NULL,
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  content text NOT NULL,
  created_at timestamptz DEFAULT now() NOT NULL,
  updated_at timestamptz DEFAULT now() NOT NULL
);

-- Enable RLS
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_reactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_comments ENABLE ROW LEVEL SECURITY;

-- Posts policies
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'posts' AND policyname = 'Users can view all posts'
  ) THEN
    CREATE POLICY "Users can view all posts"
      ON posts FOR SELECT
      TO authenticated
      USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'posts' AND policyname = 'Users can create own posts'
  ) THEN
    CREATE POLICY "Users can create own posts"
      ON posts FOR INSERT
      TO authenticated
      WITH CHECK (auth.uid() = instructor_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'posts' AND policyname = 'Users can update own posts'
  ) THEN
    CREATE POLICY "Users can update own posts"
      ON posts FOR UPDATE
      TO authenticated
      USING (auth.uid() = instructor_id)
      WITH CHECK (auth.uid() = instructor_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'posts' AND policyname = 'Users can delete own posts'
  ) THEN
    CREATE POLICY "Users can delete own posts"
      ON posts FOR DELETE
      TO authenticated
      USING (auth.uid() = instructor_id);
  END IF;
END $$;

-- Post reactions policies
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'post_reactions' AND policyname = 'Users can view all reactions'
  ) THEN
    CREATE POLICY "Users can view all reactions"
      ON post_reactions FOR SELECT
      TO authenticated
      USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'post_reactions' AND policyname = 'Users can add reactions'
  ) THEN
    CREATE POLICY "Users can add reactions"
      ON post_reactions FOR INSERT
      TO authenticated
      WITH CHECK (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'post_reactions' AND policyname = 'Users can delete own reactions'
  ) THEN
    CREATE POLICY "Users can delete own reactions"
      ON post_reactions FOR DELETE
      TO authenticated
      USING (auth.uid() = user_id);
  END IF;
END $$;

-- Post comments policies
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'post_comments' AND policyname = 'Users can view all comments'
  ) THEN
    CREATE POLICY "Users can view all comments"
      ON post_comments FOR SELECT
      TO authenticated
      USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'post_comments' AND policyname = 'Users can create comments'
  ) THEN
    CREATE POLICY "Users can create comments"
      ON post_comments FOR INSERT
      TO authenticated
      WITH CHECK (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'post_comments' AND policyname = 'Users can update own comments'
  ) THEN
    CREATE POLICY "Users can update own comments"
      ON post_comments FOR UPDATE
      TO authenticated
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'post_comments' AND policyname = 'Users can delete own comments'
  ) THEN
    CREATE POLICY "Users can delete own comments"
      ON post_comments FOR DELETE
      TO authenticated
      USING (auth.uid() = user_id);
  END IF;
END $$;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_posts_instructor_id ON posts(instructor_id);
CREATE INDEX IF NOT EXISTS idx_posts_campus_id ON posts(campus_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_post_reactions_post_id ON post_reactions(post_id);
CREATE INDEX IF NOT EXISTS idx_post_comments_post_id ON post_comments(post_id);
