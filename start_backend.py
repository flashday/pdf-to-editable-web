#!/usr/bin/env python3
"""
Backend startup script with proper Python path configuration
"""
import sys
import os

# Add parent directory to Python path so backend imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run the app
from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    print("🚀 Backend server starting on http://localhost:5000")
    print("📡 API available at http://localhost:5000/api")
    print("❤️  Health check at http://localhost:5000/health")
    app.run(debug=True, host='0.0.0.0', port=5000)
