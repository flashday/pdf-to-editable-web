"""
Main application entry point for PDF to Editable Web Layout System
Provides complete end-to-end workflow from file upload to Editor.js rendering

启动流程：
1. 创建 Flask 应用
2. 预加载 OCR 模型（PPStructureV3 等）
3. 启动 HTTP 服务

模型预加载确保用户上传 PDF 时不需要等待模型加载
"""
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from backend.api import api_bp
from backend.config import Config
from backend.services.ocr_service import preload_models, is_models_loaded, is_models_loading
from backend.services.job_cache import init_job_cache
import os
import threading
import time

def create_app(config_class=Config):
    """
    Application factory pattern
    Creates and configures the Flask application with all necessary components
    """
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)
    
    # Enable CORS for frontend-backend communication
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # Ensure required directories exist
    config_class.UPLOAD_FOLDER.mkdir(exist_ok=True)
    config_class.TEMP_FOLDER.mkdir(exist_ok=True)
    
    # 初始化任务缓存服务
    init_job_cache(config_class.TEMP_FOLDER)
    
    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Health check endpoint at root level
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'pdf-to-editable-web'}
    
    # 模型状态检查端点
    @app.route('/api/models/status')
    def models_status():
        """
        检查 OCR 模型加载状态
        
        前端可以轮询此端点，等待模型加载完成后再允许上传
        """
        return jsonify({
            'loaded': is_models_loaded(),
            'loading': is_models_loading(),
            'ready': is_models_loaded() and not is_models_loading()
        })
    
    # Serve frontend static files in production
    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
    if os.path.exists(frontend_dist):
        @app.route('/')
        def serve_frontend():
            return send_from_directory(frontend_dist, 'index.html')
        
        @app.route('/<path:path>')
        def serve_static(path):
            if os.path.exists(os.path.join(frontend_dist, path)):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, 'index.html')
    
    return app


def preload_models_async():
    """在后台线程中预加载模型"""
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
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # 在后台线程中预加载模型
    # 这样服务器可以立即启动，同时模型在后台加载
    preload_thread = threading.Thread(target=preload_models_async, daemon=True)
    preload_thread.start()
    
    print("\n" + "=" * 60)
    print("后端服务启动中...")
    print("访问 http://localhost:5000/api/models/status 查看模型加载状态")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)