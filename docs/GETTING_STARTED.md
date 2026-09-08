# Getting Started with PC Assistant

## 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Claude API key:
```bash
cp .env.example .env
```

Run the backend:
```bash
python main.py
```

The API will be available at http://localhost:8000

## 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:5173

## 3. Testing

Visit http://localhost:5173 and start chatting with ARIA!

## Environment Variables

Create a `backend/.env` file:
```
CLAUDE_API_KEY=sk-ant-...
DATABASE_URL=sqlite:///./pc_assistant.db
ARIA_NAME=ARIA
ARIA_AVATAR=🤖
ARIA_LANGUAGE=fr
```

## Troubleshooting

- Port already in use? Change port in `backend/main.py` and `frontend/vite.config.js`
- API key not working? Verify at https://console.anthropic.com/
- Missing dependencies? Run `pip install -r requirements.txt` again
