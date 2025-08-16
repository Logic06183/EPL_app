#!/usr/bin/env python3
"""
FPL Predictor Pro - Local Demo
A fully functional local version of the FPL prediction system
"""

import subprocess
import sys
import time
import threading
import webbrowser
import os
from pathlib import Path

def print_banner():
    print("=" * 60)
    print("🚀 FPL PREDICTOR PRO - LOCAL DEMO")
    print("=" * 60)
    print("Advanced Fantasy Premier League predictions with AI")
    print("Running locally on your machine for testing")
    print("=" * 60)
    print()

def check_dependencies():
    """Check if required dependencies are installed"""
    print("📋 Checking dependencies...")
    
    required_python_packages = [
        'fastapi', 'uvicorn', 'pandas', 'numpy', 'sqlite3', 
        'scikit-learn', 'requests', 'aiohttp'
    ]
    
    missing_packages = []
    
    for package in required_python_packages:
        try:
            if package == 'sqlite3':
                import sqlite3
            else:
                __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package} - MISSING")
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        for package in missing_packages:
            subprocess.run([sys.executable, "-m", "pip", "install", package])
    
    # Check if Node.js is available for frontend
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
        print("  ✅ Node.js")
    except:
        print("  ⚠️  Node.js not found - frontend may not work")
    
    print("✅ Dependencies check completed!\n")

def setup_database():
    """Initialize the local database"""
    print("🗄️  Setting up local database...")
    
    try:
        from src.database.local_db import LocalDatabase
        db = LocalDatabase()
        print("✅ Database initialized with sample data!")
        
        # Print sample data info
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        player_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM user_predictions")
        prediction_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM user_alerts")
        alert_count = cursor.fetchone()[0]
        conn.close()
        
        print(f"  📊 {player_count} players loaded")
        print(f"  🎯 {prediction_count} predictions generated")
        print(f"  🔔 {alert_count} alerts created")
        print()
        
        return True
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def start_backend():
    """Start the FastAPI backend server"""
    print("🖥️  Starting backend server...")
    
    try:
        import uvicorn
        from src.api.local_main import app
        
        # Run uvicorn in a separate thread
        def run_server():
            uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(3)
        
        # Test server
        import requests
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ Backend server running on http://localhost:8000")
                print("  📖 API docs: http://localhost:8000/docs")
                return True
        except:
            pass
        
        print("❌ Backend server failed to start")
        return False
        
    except Exception as e:
        print(f"❌ Backend startup failed: {e}")
        return False

def start_frontend():
    """Start the Next.js frontend"""
    print("\n🎨 Starting frontend server...")
    
    frontend_dir = Path("frontend")
    
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    try:
        # Check if node_modules exists
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("📦 Installing frontend dependencies...")
            subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
        
        # Start development server in background
        print("🚀 Starting development server...")
        
        def run_frontend():
            subprocess.run(['npm', 'run', 'dev'], cwd=frontend_dir)
        
        frontend_thread = threading.Thread(target=run_frontend, daemon=True)
        frontend_thread.start()
        
        # Wait for frontend to start
        time.sleep(5)
        
        print("✅ Frontend server running on http://localhost:3000")
        return True
        
    except Exception as e:
        print(f"❌ Frontend startup failed: {e}")
        print("  💡 Make sure Node.js is installed: https://nodejs.org")
        return False

def print_usage_info():
    """Print usage information"""
    print("\n" + "=" * 60)
    print("🎉 FPL PREDICTOR PRO IS RUNNING!")
    print("=" * 60)
    print()
    print("📍 Access Points:")
    print("  🌐 Web Dashboard: http://localhost:3000")
    print("  🔗 API Server: http://localhost:8000")
    print("  📖 API Documentation: http://localhost:8000/docs")
    print()
    print("👤 Demo Account:")
    print("  Username: demo_user")
    print("  Tier: Premium (all features unlocked)")
    print()
    print("🎯 Features Available:")
    print("  ✅ AI Player Predictions")
    print("  ✅ Squad Optimizer") 
    print("  ✅ Injury & Price Alerts")
    print("  ✅ Sentiment Analysis")
    print("  ✅ Live Data Updates")
    print()
    print("🔍 What to Test:")
    print("  1. View AI predictions for top players")
    print("  2. Try the squad optimizer")
    print("  3. Check injury and price alerts")
    print("  4. Browse different tabs/sections")
    print("  5. Test mobile responsiveness")
    print()
    print("🛠️  To Stop:")
    print("  Press Ctrl+C in this terminal")
    print()
    print("=" * 60)

def open_browser():
    """Open the web browser to the dashboard"""
    time.sleep(2)
    try:
        webbrowser.open('http://localhost:3000')
        print("🌐 Opened dashboard in your default browser")
    except:
        print("💡 Manually open: http://localhost:3000")

def main():
    """Main function to start the local demo"""
    print_banner()
    
    # Check dependencies
    check_dependencies()
    
    # Setup database
    if not setup_database():
        print("❌ Failed to setup database. Exiting.")
        return
    
    # Start backend
    if not start_backend():
        print("❌ Failed to start backend. Exiting.")
        return
    
    # Start frontend
    if not start_frontend():
        print("⚠️  Frontend failed to start, but backend is running.")
        print("   You can still test the API at http://localhost:8000/docs")
    
    # Open browser
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Print usage info
    print_usage_info()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down FPL Predictor Pro...")
        print("Thanks for testing the local demo!")
        sys.exit(0)

if __name__ == "__main__":
    main()