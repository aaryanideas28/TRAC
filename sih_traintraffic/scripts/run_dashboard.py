"""Launcher Script for Nexora AI Railway Traffic Control Dashboard & Backend Server.

Launches FastAPI backend server on http://localhost:8000 and Vite frontend portal.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
SRC_DIR = PROJECT_ROOT / "src"

def main():
    print("=" * 80)
    print("LAUNCHING NEXORA AI RAILWAY TRAFFIC CONTROL PORTAL")
    print("=" * 80)
    
    # Add src to sys.path
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
        
    print("\n[1/2] Starting Python FastAPI Backend Server (OR-Tools CP-SAT API)...")
    backend_cmd = [
        sys.executable,
        "-m", "uvicorn",
        "railradar.api_server:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ]
    
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)}
    )
    
    print("  -> FastAPI Server running at http://127.0.0.1:8000")
    print("  -> OpenAPI Documentation available at http://127.0.0.1:8000/docs")
    
    time.sleep(2)
    
    print("\n[2/2] Starting Vite React Command Center Dashboard...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=DASHBOARD_DIR
    )
    
    print("  -> Web Portal running at http://localhost:5173")
    print("\n" + "=" * 80)
    print("SYSTEM IS READY FOR DEMONSTRATION! Press Ctrl+C to terminate.")
    print("=" * 80)
    
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
