# Data Analyst Agent Dashboard

This is the frontend dashboard for the Data Analyst Agent, a Next.js application that provides a natural language interface for querying restaurant analytics data.

## Overview

The dashboard allows users to:
- Query restaurant data using natural language
- View dynamically generated charts and visualizations
- Maintain conversation context across multiple queries
- Upload and preview files
- Switch between dark and light themes

## Architecture

- **Framework**: Next.js 16 with App Router
- **Language**: TypeScript
- **Styling**: CSS Modules with Tailwind CSS
- **Markdown Rendering**: ReactMarkdown with syntax highlighting
- **API Communication**: Next.js API routes (proxy to backend)

## Key Features

### Components
- **Header**: Application header with theme toggle and clear chat
- **WelcomeSection**: Initial welcome screen for new conversations
- **MessageList**: Active conversation view with message history
- **Message**: Individual message component with markdown and image support
- **InputForm**: Auto-resizing textarea with file upload
- **FilePreview**: File attachment preview with thumbnails
- **TypingIndicator**: Loading indicator for AI responses

### Hooks
- **useChat**: Manages chat state, API communication, and session management
- **useTheme**: Manages theme persistence and application

### API Routes
- **/api/coding-agent/query**: Server-side proxy to backend API (solves Mixed Content issues)

## Getting Started

### Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the dashboard.

### Production Build

```bash
npm run build
npm start
```

### Docker Deployment

The dashboard is containerized and can be deployed using Docker Compose:

```bash
docker-compose up --build dashboard
```

## Configuration

### Environment Variables

- `NEXT_PUBLIC_API_URL`: Public API URL (optional, uses API route proxy by default)
- `BACKEND_URL`: Backend API URL for server-side proxy (default: `http://api:8000` in Docker)

### Next.js Configuration

The `next.config.ts` file is configured for Docker deployments with:
- `output: 'standalone'`: Creates minimal production build
- API route proxy handles backend communication

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── api/               # API routes (proxy to backend)
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Main page component
├── components/            # React components
│   ├── Header/
│   ├── WelcomeSection/
│   ├── MessageList/
│   ├── Message/
│   ├── InputForm/
│   ├── FilePreview/
│   └── TypingIndicator/
├── hooks/                 # Custom React hooks
│   ├── useChat.ts
│   └── useTheme.ts
└── types/                 # TypeScript type definitions
    └── index.ts
```

## Dependencies

- **next**: Next.js framework
- **react**: React library
- **react-markdown**: Markdown rendering
- **remark-gfm**: GitHub Flavored Markdown support
- **rehype-highlight**: Syntax highlighting for code blocks
- **highlight.js**: Code syntax highlighting styles

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Documentation](https://www.typescriptlang.org/docs)
