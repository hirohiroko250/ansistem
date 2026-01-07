// Middleware file - required for Next.js 13.5.x dev mode
// This empty middleware prevents "middleware-manifest.json not found" error

export function middleware() {
  // No-op middleware
}

// Only run on specific paths if needed
export const config = {
  matcher: [],
};
