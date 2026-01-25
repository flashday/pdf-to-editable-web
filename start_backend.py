#!/usr/bin/env python3
"""
Backend startup script with proper Python path configuration
"""
import sys
import os
import threading

# Add parent directory to Python path so backend imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run the app
from backend.app import create_app
from backend.services.ocr_service import preload_models

def preload_models_async():
    """在后台线程中预加载模型"""
    import time
    print("\n" + "=" * 60)
    print("正在后台预加载 OCR 模型，请稍候...")
    print("模型加载完成前，PDF 上传功能将被禁用")
    print("=" * 60 + "\n")
    
    start_time = time.time()
    success = preload_models()
    elapsed = time.time() - start_time
    
    if success:
        print("\n" + "=" * 60)
        print(f"✅ OCR 模型预加载完成！耗时: {elapsed:.1f} 秒")
        print("现在可以上传 PDF 文件了")
        print("=" * 60 + "\n")
    else:
        print("\n" + "=" * 60)
        print("⚠️ OCR 模型预加载失败，将在首次使用时加载")
        print("=" * 60 + "\n")

if __name__ == '__main__':
    app = create_app()
    
    # 在后台线程中预加载模型
    preload_thread = threading.Thread(target=preload_models_async, daemon=True)
    preload_thread.start()
    
    print("🚀 Backend server starting on http://localhost:5000")
    print("📡 API available at http://localhost:5000/api")
    print("❤️  Health check at http://localhost:5000/health")
    print("📊 Model status at http://localhost:5000/api/models/status")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
