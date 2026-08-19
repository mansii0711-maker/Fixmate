import os
from flask import Flask
from flask_login import LoginManager
from config import Config
from database import db, User, Category

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from routes.public import public_bp
    from routes.auth import auth_bp
    from routes.customer import customer_bp
    from routes.provider import provider_bp
    from routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(provider_bp)
    app.register_blueprint(admin_bp)

    # Context Processors for Templates
    @app.context_processor
    def inject_global_data():
        try:
            global_categories = Category.query.all()
        except Exception:
            global_categories = []
        return dict(global_categories=global_categories)

    # Ensure Upload Directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    print("Starting FixMate Server on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
