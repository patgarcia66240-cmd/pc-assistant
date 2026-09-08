# API Reference

## Base URL
`http://localhost:8000`

## Endpoints

### Health & Status
- `GET /` - Server status
- `GET /health` - Health check

### Chat (ARIA)
- `POST /api/chat/` - Send message
- `GET /api/chat/history` - Get chat history

### System
- `GET /api/system/info` - CPU, RAM, Disk info
- `GET /api/system/processes` - Running processes

### Files
- `GET /api/files/list?path=/` - List directory
- `POST /api/files/upload` - Upload file
- `GET /api/files/search?pattern=*.txt` - Search files

### Configuration
- `GET /api/config/aria` - Get ARIA config
- `PUT /api/config/aria` - Update ARIA config

## Request/Response Format

### Chat Request
```json
{
  "message": "Hello ARIA",
  "context": {}
}
```

### Chat Response
```json
{
  "response": "Hello! How can I help?",
  "context": {},
  "status": "success"
}
```

## Error Codes

- `200` - Success
- `400` - Bad request
- `404` - Not found
- `500` - Server error

## Authentication

Currently no authentication. In production, add:
- API key authentication
- JWT tokens
- Rate limiting
