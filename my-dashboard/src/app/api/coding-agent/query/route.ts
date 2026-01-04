import { NextRequest, NextResponse } from 'next/server';

/**
 * API Proxy Route for Coding Agent Query
 * 
 * This route proxies requests from the Next.js frontend (HTTPS) to the backend API (HTTP).
 * This solves the Mixed Content issue where browsers block HTTP requests from HTTPS pages.
 */

// Get backend URL from environment variable
const getBackendUrl = (): string => {
  return process.env.NEXT_PUBLIC_API_URL || 'http://18.206.135.172:8000';
};

export async function POST(req: NextRequest) {
  try {
    const backendUrl = getBackendUrl();
    const body = await req.json();

    const response = await fetch(`${backendUrl}/api/v1/coding-agent/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: 'Backend request failed', details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      {
        error: 'Failed to proxy request to backend',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// Handle OPTIONS for CORS preflight
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}

