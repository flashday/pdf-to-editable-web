#!/bin/bash
# Development startup script for PDF to Editable Web Layout System
# Starts both backend (Flask) and frontend (Vite) servers

echo "🚀 Starting PDF to Editable Web Layout System..."

# Create required directories
mkdir -p uploads temp logs

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r backend/requirements.txt --quiet

# Start backend server in background
echo "🔧 Starting backend server on port 5000..."
cd backend
python -c "from app import create_app; app = create_app(); app.run(debug=True, host='0.0.0.0', port=5000)" &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js to run the frontend."
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install --silent

# Start frontend server
echo "🎨 Starting frontend server on port 3000..."
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ System started successfully!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:5000"
echo "   API:      http://localhost:5000/api"
echo ""
echo "Press Ctrl+C to stop all servers..."

# Handle shutdown
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait
