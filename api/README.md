# Agents API Documentation

## Overview
This API provides access to the Agents system functionality through HTTP endpoints. It allows you to interact with the AI assistant, manage agents, and control voice settings.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API is open and does not require authentication. In production, you should implement appropriate authentication mechanisms.

## Endpoints

### Root
- **GET /** - Check API status
  ```json
  {
    "status": "ok",
    "message": "Agents API is running",
    "version": "1.0.0"
  }
  ```

### Agents
- **GET /agents** - List all available agents
  ```json
  {
    "agents": {
      "memory": {...},
      "search": {...},
      ...
    },
    "total": 8
  }
  ```

- **POST /agents/{agent_name}/{action}** - Enable or disable an agent
  - Parameters:
    - `agent_name`: Name of the agent
    - `action`: "enable" or "disable"
  ```json
  {
    "status": "success",
    "message": "Agent memory enabled successfully",
    "agent": "memory",
    "action": "enable"
  }
  ```

### Queries
- **POST /query** - Process a query using the master agent
  - Request body:
    ```json
    {
      "query": "What's the weather like?",
      "context": {
        "location": "New York"
      }
    }
    ```
  - Response:
    ```json
    {
      "status": "success",
      "query": "What's the weather like?",
      "response": "..."
    }
    ```

### Voice Control
- **GET /voice/status** - Get voice output status
  ```json
  {
    "status": "success",
    "voice_enabled": true,
    "current_voice": "af_sarah",
    "speed": 1.0,
    "available_voices": {...}
  }
  ```

- **POST /voice/{action}** - Manage voice settings
  - Parameters:
    - `action`: "enable", "disable", or "stop"
  ```json
  {
    "status": "success",
    "message": "Voice enabled successfully",
    "action": "enable"
  }
  ```

## Error Handling
The API returns appropriate HTTP status codes and error messages:
- 400: Bad Request (invalid parameters)
- 500: Internal Server Error (processing error)

Example error response:
```json
{
  "detail": "Invalid action. Use 'enable' or 'disable'"
}
```

## Running the API Server
```bash
# From the project root
python -m api.run
```

The API will be available at http://localhost:8000. You can access the interactive API documentation at http://localhost:8000/docs. 