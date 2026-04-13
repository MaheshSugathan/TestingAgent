#!/bin/bash

# Start script for Agent Core Runtime Web UI

echo "🚀 Starting Agent Core Runtime Web UI..."

# Check if backend is already running
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "📦 Starting backend server..."
    cd backend
    python main.py &
    BACKEND_PID=$!
    cd ..
    sleep 3
    echo "✅ Backend started (PID: $BACKEND_PID)"
else
    echo "✅ Backend already running"
fi

# Start frontend
echo "🎨 Starting frontend..."
npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null" EXIT

