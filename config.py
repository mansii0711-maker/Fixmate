import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

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

    # Razorpay Sandbox Credentials
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID') or 'rzp_test_TPwC91DITXjxKo'
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET') or 'r7auO6Ekp1rNQBAeeqXZsLAh'

    # ---------------------------------------------------------------------------
    # Flask-Mail Configuration (Forgot Password OTP)
    # Set these via environment variables — do NOT hardcode credentials.
    #
    # For Gmail:
    #   MAIL_SERVER    = smtp.gmail.com
    #   MAIL_PORT      = 587
    #   MAIL_USE_TLS   = True
    #   MAIL_USERNAME  = your_gmail@gmail.com
    #   MAIL_PASSWORD  = your_app_password   (16-char Google App Password)
    #   MAIL_SENDER    = your_gmail@gmail.com
    # ---------------------------------------------------------------------------
    MAIL_SERVER   = os.environ.get('MAIL_SERVER')   or 'smtp.gmail.com'
    MAIL_PORT     = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS',  'true').lower() in ('true', '1', 'yes')
    MAIL_USE_SSL  = os.environ.get('MAIL_USE_SSL',  'false').lower() in ('true', '1', 'yes')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'fixmate04@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'grokpkyrcyjqdrvh'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_SENDER') or 'fixmate04@gmail.com'
