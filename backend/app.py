"""
Main application entry point for PDF to Editable Web Layout System
Provides complete end-to-end workflow from file upload to Editor.js rendering
"""
from flask import Flask, send_from_directory
from flask_cors import CORS
from backend.api import api_bp
from backend.config import Config
import os

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
    
    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Health check endpoint at root level
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'pdf-to-editable-web'}
    
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

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)