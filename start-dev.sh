#!/bin/bash

echo "🚀 Starting PC Assistant Development Environment"

# Start backend
echo "📦 Starting backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Ne copie .env.example vers .env QUE si .env n'existe pas encore : avant ce fix, "cp .env.example
# .env" écrasait tes vraies clés API (Claude/Twelve Data/EODHD/Metal Sentinel) à CHAQUE lancement
# de ce script, en les remplaçant par les placeholders "your_api_key_here".
[ -f .env ] || cp .env.example .env
python main.py &
BACKEND_PID=$!

# Start frontend
echo "🎨 Starting frontend..."
cd ../frontend
npm install
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Services started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"

wait
