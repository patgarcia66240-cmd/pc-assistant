#!/bin/bash

echo "🚀 Starting PC Assistant Production Build"

# Build backend
echo "📦 Building backend..."
cd backend
pip install -r requirements.txt

# Build frontend
echo "🎨 Building frontend..."
cd ../frontend
npm install
npm run build

# Start backend with gunicorn
echo "🌐 Starting production server..."
cd ../backend
gunicorn main:app --workers 4 --host 0.0.0.0 --port 8000

