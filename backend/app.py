"""
Main application entry point for PDF to Editable Web Layout System
Provides complete end-to-end workflow from file upload to Editor.js rendering

启动流程：
1. 创建 Flask 应用
2. 顺序预加载三个服务：LLM → OCR → RAG（Embedding）
3. 启动 HTTP 服务

模型预加载确保用户使用时不需要等待模型加载
顺序加载避免 PaddlePaddle 和 PyTorch 同时加载时的资源竞争
"""
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from backend.api import api_bp
from backend.api.chatocr_routes import chatocr_bp
from backend.api.document_type_routes import document_type_bp
from backend.config import Config, ChatOCRConfig
from backend.services.ocr_service import preload_models, is_models_loaded, is_models_loading
from backend.services.job_cache import init_job_cache
import os
import threading
import time
import logging

logger = logging.getLogger(__name__)

# ============== 服务加载状态追踪 ==============
_service_status = {
    'ocr': {'loaded': False, 'loading': False, 'error': None, 'time': 0},
    'llm': {'loaded': False, 'loading': False, 'error': None, 'time': 0},
    'rag': {'loaded': False, 'loading': False, 'error': None, 'time': 0},
}
_status_lock = threading.Lock()


def get_service_status():
    """获取所有服务的加载状态"""
    with _status_lock:
        return _service_status.copy()


def _update_status(service: str, loaded: bool = None, loading: bool = None, 
                   error: str = None, time_elapsed: float = None):
    """更新服务状态"""
    with _status_lock:
        if loaded is not None:
            _service_status[service]['loaded'] = loaded
        if loading is not None:
            _service_status[service]['loading'] = loading
        if error is not None:
            _service_status[service]['error'] = error
        if time_elapsed is not None:
            _service_status[service]['time'] = time_elapsed

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
    
    # Register ChatOCR API blueprint (智能文档理解)
    if ChatOCRConfig.ENABLE_CHATOCR:
        app.register_blueprint(chatocr_bp)
        logger.info("ChatOCR API routes registered")
    
    # Register Document Type API blueprint (单据类型配置)
    app.register_blueprint(document_type_bp)
    logger.info("Document Type API routes registered")
    
    # Health check endpoint at root level
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'pdf-to-editable-web'}
    
    # 模型状态检查端点（兼容旧接口）
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
    
    # 所有服务状态检查端点
    @app.route('/api/services/status')
    def services_status():
        """
        检查所有服务（OCR、LLM、RAG）的加载状态
        
        返回:
        {
            "ocr": {"loaded": true, "loading": false, "error": null, "time": 76.8},
            "llm": {"loaded": true, "loading": false, "error": null, "time": 0.5},
            "rag": {"loaded": true, "loading": false, "error": null, "time": 3.2},
            "all_ready": true
        }
        """
        status = get_service_status()
        all_ready = all(s['loaded'] and not s['loading'] for s in status.values())
        return jsonify({
            **status,
            'all_ready': all_ready
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


# ============== 并行预加载函数 ==============

def preload_ocr_async():
    """后台线程：预加载 OCR 模型"""
    _update_status('ocr', loading=True)
    print("🔄 [OCR] 开始加载 PaddleOCR 模型...")
    
    start_time = time.time()
    try:
        success = preload_models()
        elapsed = time.time() - start_time
        
        if success:
            _update_status('ocr', loaded=True, loading=False, time_elapsed=elapsed)
            print(f"✅ [OCR] 模型加载完成！耗时: {elapsed:.1f} 秒")
        else:
            _update_status('ocr', loaded=False, loading=False, error="加载失败", time_elapsed=elapsed)
            print(f"⚠️ [OCR] 模型加载失败，耗时: {elapsed:.1f} 秒")
    except Exception as e:
        elapsed = time.time() - start_time
        _update_status('ocr', loaded=False, loading=False, error=str(e), time_elapsed=elapsed)
        print(f"❌ [OCR] 模型加载异常: {e}")


def preload_llm_async():
    """后台线程：预加载 LLM 服务（检查 Ollama 连接）"""
    if not ChatOCRConfig.ENABLE_CHATOCR:
        _update_status('llm', loaded=False, loading=False, error="ChatOCR 未启用")
        print("⏭️ [LLM] ChatOCR 未启用，跳过")
        return
    
    _update_status('llm', loading=True)
    print(f"🔄 [LLM] 检查 Ollama 服务 ({ChatOCRConfig.OLLAMA_BASE_URL})...")
    
    start_time = time.time()
    try:
        from backend.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        is_healthy = llm_service.check_health(force=True)
        elapsed = time.time() - start_time
        
        if is_healthy:
            _update_status('llm', loaded=True, loading=False, time_elapsed=elapsed)
            print(f"✅ [LLM] Ollama 服务可用，模型: {ChatOCRConfig.OLLAMA_MODEL}，耗时: {elapsed:.1f} 秒")
        else:
            _update_status('llm', loaded=False, loading=False, error="Ollama 服务不可用", time_elapsed=elapsed)
            print(f"⚠️ [LLM] Ollama 服务不可用，请确保 Ollama 已启动")
    except Exception as e:
        elapsed = time.time() - start_time
        _update_status('llm', loaded=False, loading=False, error=str(e), time_elapsed=elapsed)
        print(f"❌ [LLM] 服务检查异常: {e}")


def preload_rag_async():
    """后台线程：预加载 RAG 服务（Embedding 模型）"""
    if not ChatOCRConfig.ENABLE_RAG:
        _update_status('rag', loaded=False, loading=False, error="RAG 未启用")
        print("⏭️ [RAG] RAG 未启用，跳过")
        return
    
    _update_status('rag', loading=True)
    print(f"🔄 [RAG] 加载 Embedding 模型 ({ChatOCRConfig.EMBEDDING_MODEL})...")
    
    start_time = time.time()
    try:
        print("   [RAG] 导入 embedding_service...")
        from backend.services.embedding_service import get_embedding_service
        print("   [RAG] 导入 vector_store...")
        from backend.services.vector_store import get_vector_store
        
        # 预加载 Embedding 模型
        print("   [RAG] 初始化 EmbeddingService...")
        embedding_service = get_embedding_service()
        print("   [RAG] EmbeddingService 初始化完成")
        
        # 预加载向量存储
        print("   [RAG] 初始化 VectorStore...")
        vector_store = get_vector_store()
        print("   [RAG] VectorStore 初始化完成")
        
        elapsed = time.time() - start_time
        _update_status('rag', loaded=True, loading=False, time_elapsed=elapsed)
        print(f"✅ [RAG] Embedding 模型加载完成！耗时: {elapsed:.1f} 秒")
    except Exception as e:
        elapsed = time.time() - start_time
        _update_status('rag', loaded=False, loading=False, error=str(e), time_elapsed=elapsed)
        print(f"❌ [RAG] 模型加载异常: {e}")
        import traceback
        traceback.print_exc()
        _update_status('rag', loaded=False, loading=False, error=str(e), time_elapsed=elapsed)
        print(f"❌ [RAG] 模型加载异常: {e}")


def preload_all_services():
    """
    预加载所有服务（顺序加载）
    
    策略：完全顺序加载，避免并行时的资源竞争和冲突
    加载顺序：LLM → OCR → RAG
    """
    print("\n" + "=" * 60)
    print("🚀 预加载服务中（顺序加载模式）...")
    print("   1. LLM: Ollama 服务连接检查")
    print("   2. OCR: PaddleOCR/PPStructure 模型")
    print("   3. RAG: Embedding 向量化模型")
    print("=" * 60 + "\n")
    
    total_start = time.time()
    
    # 1. 先检查 LLM（最快）
    preload_llm_async()
    
    # 2. 加载 OCR（PaddlePaddle）
    preload_ocr_async()
    
    # 3. 最后加载 RAG（PyTorch Embedding）
    preload_rag_async()
    
    total_elapsed = time.time() - total_start
    
    # 打印最终状态
    status = get_service_status()
    print("\n" + "=" * 60)
    print(f"📊 服务加载状态汇总 (总耗时: {total_elapsed:.1f}s):")
    for name, s in status.items():
        icon = "✅" if s['loaded'] else "❌"
        time_str = f"{s['time']:.1f}s" if s['time'] > 0 else "-"
        error_str = f" ({s['error']})" if s['error'] else ""
        print(f"   {icon} {name.upper()}: {'已就绪' if s['loaded'] else '未就绪'} [{time_str}]{error_str}")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    app = create_app()
    
    # 在后台线程中并行预加载所有服务
    preload_thread = threading.Thread(target=preload_all_services, daemon=True)
    preload_thread.start()
    
    print("\n" + "=" * 60)
    print("🌐 后端服务启动中...")
    print("   访问 http://localhost:5000/api/services/status 查看服务状态")
    print("   访问 http://localhost:5000/api/models/status 查看 OCR 状态")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)