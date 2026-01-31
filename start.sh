#!/bin/bash
echo "🚀 Launching Drift-Aware Learning Platform..."

# Kill any existing processes on ports 8000 or 8501 to avoid conflicts
pkill -f "uvicorn backend.main:app"
pkill -f "streamlit run frontend/app.py"

# Start Backend in background
echo "🔌 Starting Backend Server..."
nohup python3 -m uvicorn backend.main:app --reload > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 5

# Start Frontend
echo "💻 Starting Frontend Dashboard..."
python3 -m streamlit run frontend/app.py

# Cleanup on exit
kill $BACKEND_PID
