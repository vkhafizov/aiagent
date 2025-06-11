#!/usr/bin/env python3
"""
Simple runner for the AI GitHub Explainer application.
This script starts both the FastAPI server and the scheduler.
"""

import os
import sys
import subprocess
import signal
import time
import threading
from pathlib import Path

def run_server():
    """Run the FastAPI server"""
    try:
        import uvicorn
        from app.main import app
        
        print("🚀 Starting FastAPI server...")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

def run_scheduler():
    """Run the scheduler in a separate process"""
    try:
        print("📅 Starting scheduler...")
        
        # Wait a moment for the server to start
        time.sleep(3)
        
        # Run scheduler
        import scheduler
        scheduler.main()
        
    except Exception as e:
        print(f"❌ Error starting scheduler: {e}")

def check_requirements():
    """Check if all required packages are installed"""
    required_imports = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('requests', 'requests'), 
        ('anthropic', 'anthropic'),
        ('github', 'pygithub'),  # PyGithub imports as 'github'
        ('jinja2', 'jinja2'),
        ('schedule', 'schedule'),
        ('dotenv', 'python-dotenv'),  # python-dotenv imports as 'dotenv'
        ('pydantic', 'pydantic'),
        ('pydantic_settings', 'pydantic-settings')  # New package for BaseSettings
    ]
    
    missing_packages = []
    
    for import_name, package_name in required_imports:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Install them with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📝 Create one from .env.example:")
        print("   cp .env.example .env")
        print("   # Then edit .env with your API keys")
        return False
    
    # Check for required variables
    required_vars = ['GITHUB_TOKEN', 'ANTHROPIC_API_KEY']
    missing_vars = []
    
    with open(env_file) as f:
        content = f.read()
        for var in required_vars:
            if f"{var}=" not in content or f"{var}=your_" in content:
                missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing or incomplete environment variables in .env:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n🔑 Please add your API keys to the .env file")
        return False
    
    return True

def main():
    """Main entry point"""
    print("🤖 AI GitHub Explainer")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    if not check_env_file():
        sys.exit(1)
    
    print("✅ All requirements satisfied!")
    print("🏃 Starting application...\n")
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Start the server (this will block)
        run_server()
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()