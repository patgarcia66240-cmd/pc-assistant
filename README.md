# PC Assistant - ARIA 🤖

**ARIA** (AI-powered Retrieval Intelligence Assistant) is a cross-platform PC management system with integrated AI capabilities powered by Claude API.

## Features

- 💬 **AI Chat Interface** - Talk to ARIA with voice support
- 📊 **System Monitoring** - Real-time CPU, RAM, disk monitoring
- 📁 **File Management** - Index, search, and organize files
- 🎯 **Cross-Platform** - Windows, macOS, Linux
- 🔌 **MCP Integration** - Claude Model Context Protocol support
- 🎨 **Modern UI** - Dark theme, responsive design

## Architecture

```
pc-assistant/
├── backend/        # FastAPI + Python services
├── frontend/       # React + Vite
├── desktop/        # Tauri + Rust
└── docs/          # Documentation
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Rust (for desktop app)
- Claude API key from https://console.anthropic.com/

### Installation

1. Clone and setup backend:
```bash
cd backend
cp .env.example .env
# Edit .env and add your CLAUDE_API_KEY
pip install -r requirements.txt
python main.py
```

2. Setup frontend:
```bash
cd frontend
npm install
npm run dev
```

3. Desktop (optional):
```bash
cd desktop
npm install
cargo build
```

## Configuration

Set these environment variables in `backend/.env`:
- `CLAUDE_API_KEY` - Your Anthropic API key
- `ARIA_NAME` - AI name (default: ARIA)
- `ARIA_LANGUAGE` - Language (default: fr)

## Development

- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

## License

MIT
