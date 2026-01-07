"""Flask application factory."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name: str = "default"):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    from app.config import config
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from app.routes.admin import admin_bp
    from app.routes.print import print_bp
    from app.routes.api import api_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(print_bp, url_prefix="/print")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Root redirect
    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("print.select_template"))

    # Create tables
    with app.app_context():
        db.create_all()

    return app
