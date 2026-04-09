import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { buildBackendTokenExchangePayload } from '@/lib/backend-token-exchange';

const BACKEND_URL = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

export async function POST(request: NextRequest) {
  try {
    // Get the NextAuth session
    const session = await getServerSession(authOptions);

    if (!session || !session.user) {
      return NextResponse.json(
        { error: 'Unauthorized - No session found' },
        { status: 401 }
      );
    }

    // Extract user info from session
    const { email } = session.user;

    if (!email) {
      return NextResponse.json(
        { error: 'Unauthorized - Session is missing email' },
        { status: 401 }
      );
    }

    // Call backend to exchange OAuth info for JWT token
    const response = await fetch(`${BACKEND_URL}/api/v1/auth/exchange-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(buildBackendTokenExchangePayload(session.user)),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to exchange token' },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Return the JWT token and user info
    return NextResponse.json({
      access_token: data.access_token,
      token_type: data.token_type,
      user: data.user,
    });
  } catch (error) {
    console.error('Token exchange error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
