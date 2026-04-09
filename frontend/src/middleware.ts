import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Lightweight auth middleware — only checks if a session cookie exists.
 * Avoids the full server-side session verification that next-auth/middleware
 * performs on every route transition (which adds ~1-2s latency).
 * Actual session validation is handled client-side by useSession().
 */
export function middleware(request: NextRequest) {
  // Get the actual cookie value (cookies.get() returns { name, value } or undefined)
  const sessionCookie =
    request.cookies.get('next-auth.session-token') ||
    request.cookies.get('__Secure-next-auth.session-token') ||
    request.cookies.get('backend-token');

  // Extract the value from the cookie object
  const sessionToken = sessionCookie?.value;

  if (!sessionToken) {
    const signInUrl = new URL('/auth/signin', request.url);
    const callbackPath = `${request.nextUrl.pathname}${request.nextUrl.search}`;
    signInUrl.searchParams.set('callbackUrl', callbackPath);
    return NextResponse.redirect(signInUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/writer/:path*',
    '/ai-assistant/:path*',
    '/ai-navigator/:path*',
    '/tweet-topics/:path*',
    '/rewrite/:path*',
    '/history/:path*',
    '/community/:path*',
    '/settings/:path*',
    '/workspace/:path*',
    '/account/:path*',
    '/agent/:path*',
    '/dashboard/:path*',
    '/batch/:path*',
  ],
};
