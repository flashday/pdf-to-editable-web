"""
API package for REST endpoints
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import routes to register them
from backend.api import routes
from backend.api import v3_routes  # V3 升级 API
from backend.api import workbench_routes  # 精准作业台 API