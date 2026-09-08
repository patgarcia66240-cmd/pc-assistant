#!/bin/bash

echo "🚀 Starting PC Assistant Development Environment"

# Start backend
echo "📦 Starting backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
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
