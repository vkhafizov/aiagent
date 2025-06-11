@echo off
echo Starting AI GitHub Explainer...

REM Install Python packages globally
echo Installing Python packages...
pip install fastapi uvicorn python-multipart pydantic python-dotenv requests GitPython structlog aiofiles

REM Create required directories
if not exist "backend\data\commits\hourly" mkdir "backend\data\commits\hourly"
if not exist "backend\data\posts\2h" mkdir "backend\data\posts\2h"
if not exist "backend\data\posts\24h" mkdir "backend\data\posts\24h"
if not exist "backend\logs" mkdir "backend\logs"
if not exist "logs" mkdir "logs"

REM Create .env file if it doesn't exist
if not exist "backend\.env" (
    echo Creating .env file...
    copy "backend\.env.example" "backend\.env" 2>nul || (
        echo GITHUB_TOKEN=your_token > "backend\.env"
        echo ANTHROPIC_API_KEY=your_key >> "backend\.env"
        echo APP_NAME=AI GitHub Explainer >> "backend\.env"
        echo DEBUG=true >> "backend\.env"
        echo LOG_LEVEL=INFO >> "backend\.env"
        echo OUTPUT_DIR=./data/posts >> "backend\.env"
        echo COMMIT_DATA_DIR=./data/commits >> "backend\.env"
    )
)

REM Start Backend
echo Starting Backend...
start "Backend" cmd /k "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait for backend to start
echo Waiting for backend...
timeout /t 10 /nobreak

REM Start Frontend
echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm install && npm start"

REM Wait and open browser
timeout /t 5 /nobreak
echo Opening browser...
start http://localhost:3000

echo.
echo ✅ STARTED!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
pause