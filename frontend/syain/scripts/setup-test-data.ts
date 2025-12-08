import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(supabaseUrl, supabaseAnonKey);

async function setupTestData() {
  console.log('Creating test user...');

  const testEmail = 'instructor@example.com';
  const testPassword = 'password123';

  const { data: signUpData, error: signUpError } = await supabase.auth.signUp({
    email: testEmail,
    password: testPassword,
  });

  if (signUpError) {
    console.error('Error creating user:', signUpError);
    return;
  }

  console.log('Test user created successfully!');
  console.log('Email:', testEmail);
  console.log('Password:', testPassword);

  if (signUpData.user) {
    const userId = signUpData.user.id;

    console.log('\nCreating test campuses...');
    const { data: campuses, error: campusError } = await supabase
      .from('campuses')
      .insert([
        { name: '新宿校', address: '東京都新宿区' },
        { name: '渋谷校', address: '東京都渋谷区' },
        { name: '池袋校', address: '東京都豊島区' },
      ])
      .select();

    if (campusError) {
      console.error('Error creating campuses:', campusError);
    } else {
      console.log('Campuses created:', campuses?.length);
    }

    console.log('\nSetup complete!');
    console.log('\nLogin credentials:');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('Email:    instructor@example.com');
    console.log('Password: password123');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━');
  }
}

setupTestData();