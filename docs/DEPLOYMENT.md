# Deployment Guide

## Local Development

```bash
make dev
```

## Production Deployment

### Using Docker

1. Build images:
```bash
docker-compose build
```

2. Run containers:
```bash
docker-compose up
```

### Standalone Installation

1. Install Python 3.11+
2. Install Node.js 18+
3. Run: `./start-production.sh`

## Environment Variables

Required in production:
- `CLAUDE_API_KEY` - Your Anthropic API key
- `DATABASE_URL` - PostgreSQL or SQLite connection string

## Health Checks

Verify backend is running:
```bash
curl http://localhost:8000/health
```

Verify frontend is running:
```bash
curl http://localhost:5173
```

## Logs

- Backend: stdout from uvicorn/gunicorn
- Frontend: browser console
- System: Check application logs

## Updates

To update dependencies:

```bash
cd backend && pip install -r requirements.txt --upgrade
cd frontend && npm update
```
