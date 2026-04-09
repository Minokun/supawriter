import { NextRequest, NextResponse } from 'next/server';

export const BACKEND_API =
  process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

export function buildBackendHeaders(
  request: NextRequest,
  extras: Record<string, string> = {}
): Headers {
  const headers = new Headers(extras);
  const authorization = request.headers.get('authorization');
  const cookie = request.headers.get('cookie');

  if (authorization) {
    headers.set('authorization', authorization);
  }

  if (cookie) {
    headers.set('cookie', cookie);
  }

  return headers;
}

export async function requireAdmin(request: NextRequest): Promise<NextResponse | null> {
  const headers = buildBackendHeaders(request, {
    'Content-Type': 'application/json',
  });

  if (!headers.get('authorization') && !headers.get('cookie')) {
    return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
  }

  try {
    const response = await fetch(`${BACKEND_API}/api/v1/auth/me`, {
      headers,
      cache: 'no-store',
    });

    if (response.status === 401 || response.status === 403) {
      return NextResponse.json({ error: 'Authentication required' }, { status: response.status });
    }

    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to verify user' }, { status: response.status });
    }

    const user = await response.json();

    if (!user?.is_admin) {
      return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
    }

    return null;
  } catch (error) {
    console.error('Error verifying hotspots admin access:', error);
    return NextResponse.json({ error: 'Failed to verify user' }, { status: 500 });
  }
}
