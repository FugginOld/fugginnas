from flask import Flask, render_template
from system.auth import register_auth

from routes.backend import backend_bp
from routes.nonraid import nonraid_bp
from routes.drives import drives_bp
from routes.pool import pool_bp
from routes.apply import apply_bp
from routes.mover import mover_bp
from routes.shares import shares_bp
from routes.snapraid import snapraid_bp
from routes.status import status_bp
from routes.summary import summary_bp


def create_app() -> Flask:
    app = Flask(__name__)
    register_auth(app)

    @app.get("/")
    def index():
        return render_template("index.html")

    app.register_blueprint(backend_bp)
    app.register_blueprint(nonraid_bp)
    app.register_blueprint(drives_bp)
    app.register_blueprint(pool_bp)
    app.register_blueprint(snapraid_bp)
    app.register_blueprint(mover_bp)
    app.register_blueprint(shares_bp)
    app.register_blueprint(summary_bp)
    app.register_blueprint(apply_bp)
    app.register_blueprint(status_bp)
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=7070)
