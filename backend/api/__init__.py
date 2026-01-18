"""
API package for REST endpoints
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import routes to register them
from backend.api import routes