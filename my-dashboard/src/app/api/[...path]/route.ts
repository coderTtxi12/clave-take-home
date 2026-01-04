import { NextRequest, NextResponse } from 'next/server';

/**
 * API Proxy Route
 * 
 * This route proxies requests from the Next.js frontend (HTTPS) to the backend API (HTTP).
 * This solves the Mixed Content issue where browsers block HTTP requests from HTTPS pages.
 * 
 * Usage: /api/v1/coding-agent/query -> proxies to BACKEND_URL/api/v1/coding-agent/query
 */

// Get backend URL from environment variable
const getBackendUrl = (): string => {
  // Use NEXT_PUBLIC_API_URL if set (for production)
  // Otherwise fallback to EC2 IP (for development/testing)
  // Note: In Vercel, set NEXT_PUBLIC_API_URL to http://18.206.135.172:8000
  return process.env.NEXT_PUBLIC_API_URL || 'http://18.206.135.172:8000';
};

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, 'GET');
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, 'POST');
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, 'PUT');
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, 'DELETE');
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, 'PATCH');
}

async function handleRequest(
  request: NextRequest,
  pathSegments: string[],
  method: string
) {
  try {
    const backendUrl = getBackendUrl();
    const path = pathSegments.join('/');
    const url = `${backendUrl}/${path}`;

    // Get query parameters from the request
    const searchParams = request.nextUrl.searchParams.toString();
    const fullUrl = searchParams ? `${url}?${searchParams}` : url;

    // Get request body if it exists
    let body: string | undefined;
    if (method !== 'GET' && method !== 'HEAD') {
      try {
        body = await request.text();
      } catch (e) {
        // No body or body already consumed
      }
    }

    // Forward headers (excluding host and connection)
    const headers: HeadersInit = {};
    request.headers.forEach((value, key) => {
      // Skip headers that shouldn't be forwarded
      if (
        !['host', 'connection', 'content-length'].includes(key.toLowerCase())
      ) {
        headers[key] = value;
      }
    });

    // Make request to backend
    const response = await fetch(fullUrl, {
      method,
      headers: {
        ...headers,
        'Content-Type': request.headers.get('content-type') || 'application/json',
      },
      body: body || undefined,
    });

    // Get response body
    const responseBody = await response.text();

    // Create response with same status and headers
    const nextResponse = new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
    });

    // Copy relevant headers from backend response
    response.headers.forEach((value, key) => {
      if (
        !['content-encoding', 'transfer-encoding', 'connection'].includes(
          key.toLowerCase()
        )
      ) {
        nextResponse.headers.set(key, value);
      }
    });

    // Set CORS headers to allow frontend access
    nextResponse.headers.set('Access-Control-Allow-Origin', '*');
    nextResponse.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS');
    nextResponse.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    return nextResponse;
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
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}

