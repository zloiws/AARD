AARD UI (visualizer)

Quickstart:

1. cd ui
2. npm install
3. npm run dev

The Vite dev server is configured to use port 3000. The project is a minimal React + TypeScript scaffold and contains a placeholder `DualFlowCanvas` component under `src/components/`.
Environment:

- Set `VITE_API_BASE` to the backend base URL if it's not `http://localhost:8000`, e.g. `VITE_API_BASE=http://localhost:8000`.

Behavior:

- `DualFlowCanvas` fetches the execution graph from `GET /api/execution/{session_id}/graph` (session_id via `?session_id=`) and connects to the WebSocket at `/ws/execution/{session_id}` for real-time updates. It expects the backend to send only real data (no mocks).


