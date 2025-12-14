from flask import Flask
from flask_cors import CORS
import os
import logging

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['JSON_SORT_KEYS'] = False
    
    CORS(app)
    
    logging.basicConfig(level=logging.INFO)
    
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    return app
