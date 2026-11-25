import os

from create_app import create_app

app = create_app()

if __name__ == "__main__":
    # Run from the src/ folder:  python app.py     ->  http://localhost:9999/docs
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "9999")), debug=app.config.get("DEBUG", False))


# & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
#    CREATE DATABASE IF NOT EXISTS scentstation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
#     exit
#    $env:DATABASE_URI = "mysql+pymysql://root:12345@127.0.0.1:3306/scentstation?charset=utf8mb4"
#  python src/app.py
#   http://localhost:9999/docs