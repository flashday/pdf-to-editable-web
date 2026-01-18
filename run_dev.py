#!/usr/bin/env python3
"""
Cross-platform development startup script for PDF to Editable Web Layout System
Works on Windows, macOS, and Linux
Starts both backend (Flask) and frontend (Vite) servers
"""
import os
import sys
import subprocess
import time
import platform
from pathlib import Path

def print_colored(message, color=''):
    """Print colored message (works on all platforms)"""
    colors = {
        'green': '\033[92m',
        'blue': '\033[94m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'end': '\033[0m'
    }
    if platform.system() == 'Windows':
        # Windows doesn't support ANSI colors in older terminals
        print(message)
    else:
        print(f"{colors.get(color, '')}{message}{colors['end']}")

def create_directories():
    """Create required directories"""
    print_colored("📁 Creating required directories...", 'blue')
    for dir_name in ['uploads', 'temp', 'logs']:
        Path(dir_name).mkdir(exist_ok=True)

def setup_venv():
    """Setup Python virtual environment"""
    venv_path = Path('venv')
    if not venv_path.exists():
        print_colored("📦 Creating Python virtual environment...", 'blue')
        subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
    
    # Get the correct Python executable path
    if platform.system() == 'Windows':
        python_exe = venv_path / 'Scripts' / 'python.exe'
        pip_exe = venv_path / 'Scripts' / 'pip.exe'
    else:
        python_exe = venv_path / 'bin' / 'python'
        pip_exe = venv_path / 'bin' / 'pip'
    
    return str(python_exe), str(pip_exe)

def install_python_deps(pip_exe):
    """Install Python dependencies"""
    print_colored("📦 Installing Python dependencies...", 'blue')
    subprocess.run([pip_exe, 'install', '-r', 'backend/requirements.txt', '--quiet'], check=True)

def check_node():
    """Check if Node.js is installed"""
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_backend(python_exe):
    """Start backend server"""
    print_colored("🔧 Starting backend server on port 5000...", 'blue')
    if platform.system() == 'Windows':
        # On Windows, use CREATE_NEW_PROCESS_GROUP to allow Ctrl+C handling
        backend_process = subprocess.Popen(
            [python_exe, 'start_backend.py'],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == 'Windows' else 0
        )
    else:
        backend_process = subprocess.Popen([python_exe, 'start_backend.py'])
    
    time.sleep(3)  # Wait for backend to start
    return backend_process

def start_frontend():
    """Start frontend server"""
    if not check_node():
        print_colored("❌ Node.js is not installed. Please install Node.js to run the frontend.", 'red')
        return None
    
    print_colored("📦 Installing frontend dependencies...", 'blue')
    subprocess.run(['npm', 'install', '--silent'], cwd='frontend', check=True)
    
    print_colored("🎨 Starting frontend server on port 3000...", 'blue')
    frontend_process = subprocess.Popen(['npm', 'run', 'dev'], cwd='frontend')
    
    return frontend_process

def main():
    """Main function"""
    print_colored("🚀 Starting PDF to Editable Web Layout System...", 'green')
    print()
    
    try:
        # Setup
        create_directories()
        python_exe, pip_exe = setup_venv()
        install_python_deps(pip_exe)
        
        # Start servers
        backend_process = start_backend(python_exe)
        frontend_process = start_frontend()
        
        if frontend_process is None:
            backend_process.terminate()
            return 1
        
        # Print success message
        print()
        print_colored("✅ System started successfully!", 'green')
        print_colored("   Frontend: http://localhost:3000 or http://127.0.0.1:3000", 'blue')
        print_colored("   Backend:  http://localhost:5000 or http://127.0.0.1:5000", 'blue')
        print_colored("   API:      http://localhost:5000/api", 'blue')
        print()
        print_colored("Press Ctrl+C to stop all servers...", 'yellow')
        print()
        
        # Wait for processes
        try:
            backend_process.wait()
            frontend_process.wait()
        except KeyboardInterrupt:
            print()
            print_colored("🛑 Shutting down servers...", 'yellow')
            backend_process.terminate()
            frontend_process.terminate()
            backend_process.wait()
            frontend_process.wait()
            print_colored("✅ Servers stopped successfully!", 'green')
    
    except Exception as e:
        print_colored(f"❌ Error: {e}", 'red')
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
