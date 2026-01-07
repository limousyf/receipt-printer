#!/usr/bin/env python3
"""Entry point for the Receipt Printer application."""
import os
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "default"))

if __name__ == "__main__":
    # Get host and port from environment or use defaults
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "default") == "development"

    print(f"Starting Receipt Printer on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
