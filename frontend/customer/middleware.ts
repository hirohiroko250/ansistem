/**
 * Next.js Middleware - 認証・ルーティング制御
 *
 * - 認証が必要なページへの未認証アクセスを/loginへリダイレクト
 * - 認証済みユーザーの公開ページ（login, signup等）へのアクセスを/feedへリダイレクト
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// 認証が不要な公開ページ
const PUBLIC_PATHS = [
  '/login',
  '/signup',
  '/password-reset',
  '/trial',
  '/map',
];

// 認証チェックをスキップするパス（静的ファイル等）
const SKIP_PATHS = [
  '/_next',
  '/api',
  '/icons',
  '/images',
  '/manifest.json',
  '/favicon.ico',
  '/oza-logo.svg',
];

// 認証トークンのクッキー名（localStorage は middleware で読めないため）
// 注: 実際の認証チェックはクライアントサイドで行う
const ACCESS_TOKEN_COOKIE = 'access_token';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 静的ファイル等はスキップ
  if (SKIP_PATHS.some((path) => pathname.startsWith(path))) {
    return NextResponse.next();
  }

  // クッキーから認証状態を確認
  // 注: JWT の詳細な検証はクライアントサイドで行う
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  const isAuthenticated = !!accessToken;

  // 公開ページかどうかを判定
  const isPublicPath = PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`)
  );

  // 認証済みユーザーが公開ページにアクセスした場合
  if (isAuthenticated && isPublicPath) {
    // /feed へリダイレクト（ログイン後のデフォルトページ）
    return NextResponse.redirect(new URL('/feed', request.url));
  }

  // 未認証ユーザーが認証必要ページにアクセスした場合
  // 注: 現在の実装では localStorage でトークン管理しているため、
  //     この判定は参考程度。実際のリダイレクトはクライアントサイドで行う。
  // if (!isAuthenticated && !isPublicPath) {
  //   return NextResponse.redirect(new URL('/login', request.url));
  // }

  return NextResponse.next();
}

export const config = {
  // マッチするパスを指定
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
