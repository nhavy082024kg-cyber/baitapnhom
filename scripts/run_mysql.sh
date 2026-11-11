#!/usr/bin/env bash
# Start a local MySQL 8 in Docker (data kept in the volume `scentstation_mysql`).
#   bash scripts/run_mysql.sh
docker run -d --name scentstation-mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=scentstation \
  -p 3306:3306 \
  -v scentstation_mysql:/var/lib/mysql \
  mysql:8.0 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

echo "MySQL is starting. DATABASE_URI=mysql+pymysql://root:password@127.0.0.1:3306/scentstation?charset=utf8mb4"
