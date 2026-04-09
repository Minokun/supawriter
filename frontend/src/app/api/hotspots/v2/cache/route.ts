import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_API, buildBackendHeaders, requireAdmin } from '../_utils';

export const dynamic = 'force-dynamic';

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const source = searchParams.get('source');
  const authError = await requireAdmin(request);

  if (authError) {
    return authError;
  }

  try {
    const url = source
      ? `${BACKEND_API}/api/v1/hotspots/v2/cache?source=${source}`
      : `${BACKEND_API}/api/v1/hotspots/v2/cache`;

    const response = await fetch(url, {
      method: 'DELETE',
      headers: buildBackendHeaders(request, {
        'Content-Type': 'application/json',
      }),
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to clear cache' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error clearing cache:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
