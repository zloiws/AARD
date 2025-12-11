# Execution API

Endpoints:

- GET `/api/execution/{session_id}/graph`  
  Returns the execution graph (nodes and edges) for the given chat session.

- GET `/api/execution/{session_id}/node/{node_id}`  
  Returns details for a specific execution node.

- POST `/api/execution/{session_id}/replay/{node_id}`  
  Request a replay of a node execution (placeholder — integration with execution engine required).

Notes:
- Responses follow simple JSON shapes; nodes and edges include stringified UUIDs and timestamps.


