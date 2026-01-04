/**
 * API Proxy Route for Coding Agent Query
 * 
 * This Next.js API route acts as a server-side proxy between the frontend
 * and the backend API. It solves several issues:
 * 
 * 1. Mixed Content: Browsers block HTTP requests from HTTPS pages.
 *    This proxy allows the frontend to make same-origin requests.
 * 
 * 2. Docker Networking: When running in Docker Compose, the Next.js
 *    server can use Docker service names (api:8000) for internal
 *    communication, while the browser only sees relative URLs.
 * 
 * 3. Security: Backend URLs are not exposed to the client.
 * 
 * The route forwards POST requests to the backend API and returns
 * the response. It also handles CORS preflight requests (OPTIONS).
 */
import { NextRequest, NextResponse } from 'next/server';

/**
 * Get the backend API URL for proxying requests.
 * 
 * Priority:
 * 1. BACKEND_URL environment variable (if set)
 * 2. Docker service name 'http://api:8000' (default for Docker Compose)
 * 
 * Note: This runs server-side only, so it can use Docker service names
 * that are not accessible from the browser.
 * 
 * @returns Backend API base URL
 */
const getBackendUrl = (): string => {
  // If BACKEND_URL is set, use it
  if (process.env.BACKEND_URL) {
    return process.env.BACKEND_URL;
  }
  // In Docker, use the service name (internal Docker network)
  // This works because the Next.js server runs inside Docker
  return 'http://api:8000';
};

/**
 * Handle POST requests to the coding agent query endpoint.
 * 
 * This function:
 * 1. Receives the request from the frontend
 * 2. Forwards it to the backend API
 * 3. Returns the backend response to the frontend
 * 
 * @param req - Next.js request object containing the query and session_id
 * @returns Next.js response with the backend API result
 */
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

/**
 * Handle OPTIONS requests for CORS preflight.
 * 
 * Browsers send OPTIONS requests before POST requests to check CORS
 * permissions. This handler allows all origins, methods, and headers
 * for simplicity (can be restricted in production).
 * 
 * @returns Next.js response with CORS headers
 */
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

