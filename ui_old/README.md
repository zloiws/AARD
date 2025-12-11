# AARD UI - Modern Next.js Frontend

Modern, responsive frontend for the AARD (AI Agent Research Dashboard) platform built with Next.js 15, React 19, and Tailwind CSS 4.0.

## ✨ Features

- **Mission Control Dashboard**: Real-time monitoring of AI agent workflows with live metrics
- **Workflow Builder**: Visual graph-based workflow editor using React Flow
- **Command Palette**: Quick access to all features with Cmd+K
- **Real-time Updates**: WebSocket integration for live workflow events
- **Toast Notifications**: User-friendly notifications using Sonner
- **Smooth Animations**: Framer Motion for polished transitions
- **Dark Mode**: Full dark mode support
- **Type-Safe API**: Complete TypeScript coverage with TanStack Query
- **E2E Testing**: Playwright tests for critical user flows

## 🚀 Tech Stack

- **Framework**: Next.js 15 (App Router)
- **UI Library**: React 19
- **Styling**: Tailwind CSS 4.0
- **Components**: shadcn/ui, Radix UI
- **State Management**: Zustand, TanStack Query
- **Animations**: Framer Motion
- **Workflow Visualization**: React Flow
- **Testing**: Playwright
- **Type Safety**: TypeScript

## 📦 Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running (default: http://localhost:8000)

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### Development

Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Building for Production

```bash
npm run build
npm run start
```

### Testing

Run E2E tests:
```bash
npm run test
```

Run tests with UI:
```bash
npm run test:ui
```

Debug tests:
```bash
npm run test:debug
```

## 📁 Project Structure

```
ui/
├── app/                    # Next.js app directory
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Homepage (Mission Control)
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── dashboard/        # Dashboard components
│   ├── workflow/         # Workflow builder components
│   ├── command-palette.tsx
│   └── animations.tsx
├── lib/                   # Utilities and hooks
│   ├── api/              # API client
│   ├── hooks/            # Custom React hooks
│   ├── providers/        # Context providers
│   └── utils.ts          # Utility functions
├── tests/                 # E2E tests
│   └── e2e/              # Playwright tests
└── public/               # Static assets
```

## 🎮 Key Features

### Command Palette
Press `Cmd+K` (or `Ctrl+K` on Windows) to open the command palette for quick navigation.

### API Integration
The app uses TanStack Query for data fetching with automatic caching, refetching, and optimistic updates.

### WebSocket Support
Real-time updates for task status, agent activity, and workflow events.

### Workflow Builder
Visual workflow editor with drag-and-drop nodes representing agents and tools.

## 🌍 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | `ws://localhost:8000/ws` |

## 🚢 Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Import project in Vercel
3. Set environment variables
4. Deploy

```bash
# Or use Vercel CLI
npm i -g vercel
vercel
```

### Self-Hosted

Build and run with Node.js:

```bash
npm run build
npm run start
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

## 📝 License

MIT
