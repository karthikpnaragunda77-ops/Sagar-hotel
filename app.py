import os
from flask import Flask, render_template, session
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Vercel uses a read-only deployment filesystem.
    # Only create upload folders when running locally.
    if os.environ.get("VERCEL") != "1":
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.QRCODE_FOLDER, exist_ok=True)

    # =========================
    # Register Blueprints
    # =========================

    from routes.auth_routes import auth_bp
    from routes.user_routes import user_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    # =========================
    # Global Template Variables
    # =========================

    @app.context_processor
    def inject_global_vars():
        return {
            "hotel_name": "Smart Breakfast Hotel",
            "hotel_tagline": "Authentic, Fresh & Fast Morning Delights",
            "current_table": session.get("table_number"),
            "user_logged_in": "user_id" in session,
            "user_name": session.get("user_name"),
            "admin_logged_in": session.get("is_admin", False),
            "admin_name": session.get("admin_name"),
        }

    # =========================
    # Error Handlers
    # =========================

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500

    return app


# Vercel/Gunicorn uses this Flask application object
app = create_app()


# =========================
# Local Development
# =========================

if __name__ == "__main__":
    host = getattr(Config, "HOST", "0.0.0.0")
    port = int(getattr(Config, "PORT", 5000))
    debug = getattr(Config, "DEBUG", True)

    print(
        f"Starting Smart Breakfast Hotel server "
        f"on http://{host}:{port}"
    )

    app.run(
        host=host,
        port=port,
        debug=debug
    )
