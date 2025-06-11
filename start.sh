#!/bin/bash

# STARTUP SCRIPT FOR AI GITHUB EXPLAINER
# This script starts both backend and frontend together

echo "🚀 Starting AI GitHub Explainer - Backend + Frontend"
echo "===================================================="

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    if command -v lsof > /dev/null; then
        lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
    else
        netstat -an | grep ":$1 " > /dev/null 2>&1
    fi
}

# Kill existing processes
echo -e "${YELLOW}🧹 Cleaning up existing processes...${NC}"
if check_port 8000; then
    echo "Stopping existing backend on port 8000..."
    pkill -f "uvicorn.*8000" 2>/dev/null || true
    sleep 2
fi

if check_port 3000; then
    echo "Stopping existing frontend on port 3000..."
    pkill -f "react-scripts start" 2>/dev/null || true
    pkill -f "npm start" 2>/dev/null || true
    sleep 2
fi

# Create logs directory
mkdir -p logs

echo -e "${BLUE}📁 Checking directories...${NC}"

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Error: backend and frontend directories not found!${NC}"
    echo "Please run this script from the project root directory."
    echo "Directory structure should be:"
    echo "  project-root/"
    echo "    ├── backend/"
    echo "    └── frontend/"
    exit 1
fi

echo -e "${GREEN}✅ Directory structure OK${NC}"

# Start Backend
echo -e "${YELLOW}🔧 Starting Backend (FastAPI)...${NC}"
cd backend

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo -e "${RED}❌ Could not find virtual environment activation script${NC}"
    exit 1
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -q fastapi uvicorn python-multipart pydantic python-dotenv requests GitPython structlog aiofiles

# Create required directories
mkdir -p data/commits/hourly
mkdir -p data/posts/2h
mkdir -p data/posts/24h
mkdir -p logs

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start backend in background
echo -e "${BLUE}Starting FastAPI server on http://localhost:8000${NC}"
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../.backend.pid

cd ..

# Wait for backend to start
echo -e "${YELLOW}⏳ Waiting for backend to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend failed to start in 30 seconds${NC}"
        echo "Check logs/backend.log for details"
        exit 1
    fi
done

# Start Frontend
echo -e "${YELLOW}🎨 Starting Frontend (React)...${NC}"
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
    npm install
fi

# Create .env.local for React
echo "REACT_APP_API_URL=http://localhost:8000" > .env.local

# Start frontend in background
echo -e "${BLUE}Starting React development server on http://localhost:3000${NC}"
nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.frontend.pid

cd ..

# Wait for frontend to start
echo -e "${YELLOW}⏳ Waiting for frontend to start...${NC}"
for i in {1..60}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
    if [ $i -eq 60 ]; then
        echo -e "${YELLOW}⚠️ Frontend taking longer than expected${NC}"
        echo "It may still be starting up..."
        break
    fi
done

# Success message
echo ""
echo -e "${GREEN}🎉 SUCCESS! Both services are running:${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${BLUE}🌐 Frontend:${NC} http://localhost:3000"
echo -e "${BLUE}🔧 Backend API:${NC} http://localhost:8000"
echo -e "${BLUE}📚 API Docs:${NC} http://localhost:8000/docs"
echo -e "${BLUE}💚 Health Check:${NC} http://localhost:8000/health"
echo ""
echo -e "${YELLOW}📋 Demo Instructions:${NC}"
echo "1. Open http://localhost:3000 in your browser"
echo "2. The frontend will automatically connect to the backend"
echo "3. Select either '2h' or '24h' time period"
echo "4. Click 'Generate Posts' to create AI-generated social media content"
echo "5. The system will analyze GitHub commits and create engaging posts"
echo ""
echo -e "${YELLOW}🔄 The demo will:${NC}"
echo "• Connect to QuantumFusion-network/qf-polkavm-sdk repository"
echo "• Analyze recent commits for the selected time period"
echo "• Generate multiple social media posts using AI"
echo "• Display posts with hashtags and engagement metrics"
echo ""
echo -e "${YELLOW}📊 Process IDs:${NC}"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo -e "${YELLOW}📝 View Logs:${NC}"
echo "Backend logs: tail -f logs/backend.log"
echo "Frontend logs: tail -f logs/frontend.log"
echo ""
echo -e "${RED}🛑 To stop all services:${NC}"
echo "./stop.sh"
echo "or manually: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo -e "${GREEN}✨ Ready for demo! Open http://localhost:3000 to get started.${NC}"

# Create stop script
cat > stop.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping AI GitHub Explainer services..."

if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    kill $BACKEND_PID 2>/dev/null && echo "✅ Backend stopped"
    rm .backend.pid
fi

if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    kill $FRONTEND_PID 2>/dev/null && echo "✅ Frontend stopped"
    rm .frontend.pid
fi

# Backup kill by process name
pkill -f "uvicorn.*8000" 2>/dev/null
pkill -f "react-scripts start" 2>/dev/null
pkill -f "npm start" 2>/dev/null

echo "🏁 All services stopped!"
EOF

chmod +x stop.sh

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    ./stop.sh
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Keep script running and show status
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services...${NC}"
echo -e "${BLUE}Services are running. Check the URLs above to access the application.${NC}"

# Monitor services
while true; do
    sleep 10
    
    # Check if services are still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${RED}❌ Backend process died!${NC}"
        break
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${RED}❌ Frontend process died!${NC}"
        break
    fi
done

wait