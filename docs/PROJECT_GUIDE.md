# PC Assistant Project Guide

## Overview

PC Assistant is a modular AI-powered system management platform with three main components.

## Components

### Backend (FastAPI)
- REST API server
- Claude API integration
- System monitoring services
- File management services
- Database (SQLite)

### Frontend (React + Vite)
- Chat interface
- System monitor dashboard
- File manager
- Configuration panel
- Voice input/output support

### Desktop (Tauri)
- Native desktop application
- System tray integration
- File dialogs
- Cross-platform support

## Key Services

### Chat Service
- Handles Claude API communication
- Maintains conversation context
- Manages message history

### System Service
- CPU/RAM/Disk monitoring
- Process listing
- Performance metrics

### File Service
- Directory listing
- File search
- Metadata extraction

## API Endpoints

- `GET /` - Health check
- `POST /api/chat/` - Send message
- `GET /api/system/info` - System metrics
- `GET /api/system/processes` - Process list
- `GET /api/files/list` - List files
- `GET /api/config/aria` - Get ARIA config

## Database Schema

Tables:
- `conversations` - Chat history
- `messages` - Individual messages
- `system_logs` - System metrics
- `files` - Indexed files

## Development Workflow

1. Create feature branch: `git checkout -b feature/name`
2. Make changes
3. Test locally
4. Commit with conventional commits: `git commit -m "feat: description"`
5. Push and create PR

## Deployment

### Web Deployment
```bash
cd backend
gunicorn main:app --workers 4
```

### Desktop Deployment
```bash
cd desktop
cargo tauri build
```

The installer will be in `desktop/src-tauri/target/release/`
