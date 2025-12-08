// Supabase client is mocked as per user request to remove Supabase dependency.
// This allows the build to pass without NEXT_PUBLIC_SUPABASE_URL env vars.
// The actual logic should be migrated to use the Django API.

export const supabase = {
    from: (table: string) => ({
        select: () => Promise.resolve({ data: [], error: null }),
        insert: () => Promise.resolve({ data: null, error: null }),
        update: () => Promise.resolve({ data: null, error: null }),
        delete: () => Promise.resolve({ data: null, error: null }),
        eq: () => ({ single: () => Promise.resolve({ data: null, error: null }) }),
        // Add other chainable methods as needed by the app to prevent runtime crashes during build/rendering
        order: () => ({ limit: () => Promise.resolve({ data: [], error: null }) }),
    }),
    auth: {
        getSession: () => Promise.resolve({ data: { session: null }, error: null }),
        getUser: () => Promise.resolve({ data: { user: null }, error: null }),
        signInWithPassword: () => Promise.resolve({ data: { user: null, session: null }, error: null }),
        signOut: () => Promise.resolve({ error: null }),
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => { } } } }),
        signUp: () => Promise.resolve({ data: null, error: null }),
    },
    storage: {
        from: () => ({
            upload: () => Promise.resolve({ data: null, error: null }),
            getPublicUrl: () => ({ data: { publicUrl: '' } }),
        }),
    },
} as any;
