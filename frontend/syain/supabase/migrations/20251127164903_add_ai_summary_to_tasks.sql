/*
  # Add AI Summary Fields to Tasks Table

  1. Changes
    - Add `ai_summary` column to store short AI-generated summaries (50-100 chars)
    - Add `ai_detailed_summary` column to store detailed AI analysis
    - Add `ai_next_actions` column to store suggested next actions
    - Add `ai_summary_updated_at` column to track when AI summary was last generated

  2. Notes
    - These fields will be populated by AI processing of task comments
    - Used in Smart Note feature for quick task overview
*/

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'tasks' AND column_name = 'ai_summary'
  ) THEN
    ALTER TABLE tasks ADD COLUMN ai_summary text DEFAULT '';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'tasks' AND column_name = 'ai_detailed_summary'
  ) THEN
    ALTER TABLE tasks ADD COLUMN ai_detailed_summary text DEFAULT '';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'tasks' AND column_name = 'ai_next_actions'
  ) THEN
    ALTER TABLE tasks ADD COLUMN ai_next_actions text DEFAULT '';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'tasks' AND column_name = 'ai_summary_updated_at'
  ) THEN
    ALTER TABLE tasks ADD COLUMN ai_summary_updated_at timestamptz;
  END IF;
END $$;