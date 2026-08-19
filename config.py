import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Robust, zero-dependency .env loader ensuring local variables are ALWAYS populated
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip().strip("'").strip('"')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fixmate-super-secret-key-2026'
    
    # MySQL Workbench Database Connection
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:admin@localhost/fixmate_db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'documents')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

    # SMTP Email Server Settings for Real Gmail OTP Delivery
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'mansiproject21@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'qncg rcoo penw qhld'

    # Razorpay API Credentials (Test Mode)
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
