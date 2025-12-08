/*
  # Add INSERT Policy for Profiles Table

  1. Changes
    - Add INSERT policy to allow authenticated users to create their own profile
    
  2. Security
    - Users can only insert a profile with their own user ID
    - Ensures users cannot create profiles for other users
*/

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'profiles' 
    AND policyname = 'Users can insert own profile'
  ) THEN
    CREATE POLICY "Users can insert own profile"
      ON profiles
      FOR INSERT
      TO authenticated
      WITH CHECK (auth.uid() = id);
  END IF;
END $$;
