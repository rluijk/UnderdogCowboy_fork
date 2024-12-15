from flask import Flask, send_from_directory
from pathlib import Path  # Import Path for safer path operations

def create_app():
    app = Flask(__name__, static_folder="react_ui/static")

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_react(path):
        static_folder_path = Path(app.static_folder)  # Convert static_folder to a Path object

        # Serve static files (e.g., JS, CSS)
        if path and (static_folder_path / path).exists():
            return send_from_directory(app.static_folder, path)

        # Fallback to index.html for unmatched routes
        return send_from_directory("react_ui", "index.html")

    return app
