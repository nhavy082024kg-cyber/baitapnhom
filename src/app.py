import os

from create_app import create_app

app = create_app()

if __name__ == "__main__":
    # Run from the src/ folder:  python app.py     ->  http://localhost:9999/docs
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "9999")), debug=app.config.get("DEBUG", False))
