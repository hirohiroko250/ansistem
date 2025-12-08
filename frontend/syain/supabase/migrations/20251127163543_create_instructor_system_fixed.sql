/*
  # Instructor Management System Database Schema

  1. New Tables
    - `profiles` - User profiles for instructors
    - `campuses` - Campus locations
    - `instructor_campuses` - Junction table for instructor-campus relationships
    - `classes` - Class sessions
    - `students` - Student information
    - `class_students` - Junction table for class-student relationships
    - `attendance` - Student attendance records
    - `work_logs` - Instructor check-in/check-out logs
    - `daily_reports` - Daily class reports
    - `chat_groups` - Chat group information
    - `chat_members` - Chat group memberships
    - `chat_messages` - Chat messages
    - `chat_read_status` - Message read status
    - `tasks` - Task assignments
    - `task_comments` - Task discussion threads

  2. Security
    - Enable RLS on all tables
    - Restrictive policies ensuring users can only access their own data
*/

-- Create profiles table
CREATE TABLE IF NOT EXISTS profiles (
  id uuid PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
  full_name text NOT NULL DEFAULT '',
  phone text DEFAULT '',
  email text DEFAULT '',
  role text NOT NULL DEFAULT 'instructor',
  profile_completed boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Create campuses table
CREATE TABLE IF NOT EXISTS campuses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  address text DEFAULT '',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE campuses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can view campuses"
  ON campuses FOR SELECT
  TO authenticated
  USING (true);

-- Create instructor_campuses table
CREATE TABLE IF NOT EXISTS instructor_campuses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instructor_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  campus_id uuid REFERENCES campuses(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  UNIQUE(instructor_id, campus_id)
);

ALTER TABLE instructor_campuses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Instructors can view their campuses"
  ON instructor_campuses FOR SELECT
  TO authenticated
  USING (auth.uid() = instructor_id);

CREATE POLICY "Instructors can insert their campuses"
  ON instructor_campuses FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = instructor_id);

CREATE POLICY "Instructors can delete their campuses"
  ON instructor_campuses FOR DELETE
  TO authenticated
  USING (auth.uid() = instructor_id);

-- Create classes table
CREATE TABLE IF NOT EXISTS classes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campus_id uuid REFERENCES campuses(id) ON DELETE CASCADE,
  class_name text NOT NULL,
  classroom text DEFAULT '',
  instructor_id uuid REFERENCES profiles(id) ON DELETE SET NULL,
  date date NOT NULL,
  start_time time NOT NULL,
  end_time time NOT NULL,
  status text DEFAULT 'scheduled',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE classes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Instructors can view their classes"
  ON classes FOR SELECT
  TO authenticated
  USING (auth.uid() = instructor_id);

CREATE POLICY "Instructors can update their classes"
  ON classes FOR UPDATE
  TO authenticated
  USING (auth.uid() = instructor_id)
  WITH CHECK (auth.uid() = instructor_id);

-- Create students table
CREATE TABLE IF NOT EXISTS students (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  grade text DEFAULT '',
  campus_id uuid REFERENCES campuses(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE students ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can view students"
  ON students FOR SELECT
  TO authenticated
  USING (true);

-- Create class_students table
CREATE TABLE IF NOT EXISTS class_students (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id uuid REFERENCES classes(id) ON DELETE CASCADE,
  student_id uuid REFERENCES students(id) ON DELETE CASCADE,
  is_substitute boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  UNIQUE(class_id, student_id)
);

ALTER TABLE class_students ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Instructors can view students in their classes"
  ON class_students FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM classes
      WHERE classes.id = class_students.class_id
      AND classes.instructor_id = auth.uid()
    )
  );

-- Create attendance table
CREATE TABLE IF NOT EXISTS attendance (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id uuid REFERENCES classes(id) ON DELETE CASCADE,
  student_id uuid REFERENCES students(id) ON DELETE CASCADE,
  status text DEFAULT 'present',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(class_id, student_id)
);

ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Instructors can view attendance for their classes"
  ON attendance FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM classes
      WHERE classes.id = attendance.class_id
      AND classes.instructor_id = auth.uid()
    )
  );

CREATE POLICY "Instructors can insert attendance for their classes"
  ON attendance FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM classes
      WHERE classes.id = attendance.class_id
      AND classes.instructor_id = auth.uid()
    )
  );

CREATE POLICY "Instructors can update attendance for their classes"
  ON attendance FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM classes
      WHERE classes.id = attendance.class_id
      AND classes.instructor_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM classes
      WHERE classes.id = attendance.class_id
      AND classes.instructor_id = auth.uid()
    )
  );

-- Create work_logs table
CREATE TABLE IF NOT EXISTS work_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instructor_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  campus_id uuid REFERENCES campuses(id) ON DELETE CASCADE,
  check_in_time timestamptz,
  check_out_time timestamptz,
  daily_report text DEFAULT '',
  date date NOT NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE work_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Instructors can view their work logs"
  ON work_logs FOR SELECT
  TO authenticated
  USING (auth.uid() = instructor_id);

CREATE POLICY "Instructors can insert their work logs"
  ON work_logs FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = instructor_id);

CREATE POLICY "Instructors can update their work logs"
  ON work_logs FOR UPDATE
  TO authenticated
  USING (auth.uid() = instructor_id)
  WITH CHECK (auth.uid() = instructor_id);

-- Create daily_reports table
CREATE TABLE IF NOT EXISTS daily_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id uuid REFERENCES classes(id) ON DELETE CASCADE,
  instructor_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  report_content text NOT NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE daily_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Instructors can view their daily reports"
  ON daily_reports FOR SELECT
  TO authenticated
  USING (auth.uid() = instructor_id);

CREATE POLICY "Instructors can insert their daily reports"
  ON daily_reports FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = instructor_id);

-- Create chat_groups table
CREATE TABLE IF NOT EXISTS chat_groups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  type text DEFAULT 'personal',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE chat_groups ENABLE ROW LEVEL SECURITY;

-- Create chat_members table first (before chat_groups policy references it)
CREATE TABLE IF NOT EXISTS chat_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id uuid REFERENCES chat_groups(id) ON DELETE CASCADE,
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  UNIQUE(group_id, user_id)
);

ALTER TABLE chat_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view memberships in their groups"
  ON chat_members FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

-- Now add chat_groups policy that references chat_members
CREATE POLICY "Users can view groups they are members of"
  ON chat_groups FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_members
      WHERE chat_members.group_id = chat_groups.id
      AND chat_members.user_id = auth.uid()
    )
  );

-- Create chat_messages table
CREATE TABLE IF NOT EXISTS chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id uuid REFERENCES chat_groups(id) ON DELETE CASCADE,
  sender_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  content text NOT NULL,
  is_pinned boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Members can view messages in their groups"
  ON chat_messages FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_members
      WHERE chat_members.group_id = chat_messages.group_id
      AND chat_members.user_id = auth.uid()
    )
  );

CREATE POLICY "Members can insert messages in their groups"
  ON chat_messages FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM chat_members
      WHERE chat_members.group_id = chat_messages.group_id
      AND chat_members.user_id = auth.uid()
    )
    AND sender_id = auth.uid()
  );

CREATE POLICY "Senders can update their messages"
  ON chat_messages FOR UPDATE
  TO authenticated
  USING (sender_id = auth.uid())
  WITH CHECK (sender_id = auth.uid());

-- Create chat_read_status table
CREATE TABLE IF NOT EXISTS chat_read_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id uuid REFERENCES chat_messages(id) ON DELETE CASCADE,
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  read_at timestamptz DEFAULT now(),
  UNIQUE(message_id, user_id)
);

ALTER TABLE chat_read_status ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their read status"
  ON chat_read_status FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can insert their read status"
  ON chat_read_status FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  description text DEFAULT '',
  assigned_to uuid REFERENCES profiles(id) ON DELETE CASCADE,
  assigned_by uuid REFERENCES profiles(id) ON DELETE SET NULL,
  status text DEFAULT 'not_started',
  due_date timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view tasks assigned to them"
  ON tasks FOR SELECT
  TO authenticated
  USING (auth.uid() = assigned_to OR auth.uid() = assigned_by);

CREATE POLICY "Users can update tasks assigned to them"
  ON tasks FOR UPDATE
  TO authenticated
  USING (auth.uid() = assigned_to)
  WITH CHECK (auth.uid() = assigned_to);

-- Create task_comments table
CREATE TABLE IF NOT EXISTS task_comments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id uuid REFERENCES tasks(id) ON DELETE CASCADE,
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  content text NOT NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE task_comments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view comments on their tasks"
  ON task_comments FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM tasks
      WHERE tasks.id = task_comments.task_id
      AND (tasks.assigned_to = auth.uid() OR tasks.assigned_by = auth.uid())
    )
  );

CREATE POLICY "Users can insert comments on their tasks"
  ON task_comments FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM tasks
      WHERE tasks.id = task_comments.task_id
      AND (tasks.assigned_to = auth.uid() OR tasks.assigned_by = auth.uid())
    )
    AND user_id = auth.uid()
  );