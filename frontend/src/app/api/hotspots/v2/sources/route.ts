import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_API, buildBackendHeaders } from '../_utils';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_API}/api/v1/hotspots/v2/sources`, {
      headers: buildBackendHeaders(request, {
        'Content-Type': 'application/json',
      }),
      cache: 'no-store',
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to fetch sources' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching sources:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
