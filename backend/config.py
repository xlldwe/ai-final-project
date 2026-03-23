import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('FLASK_DEBUG', 'True') == 'True'
    PORT = int(os.getenv('FLASK_PORT', 5000))
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    DB_PATH = os.getenv('BACKEND_DB_PATH', 'backend/shop.db')