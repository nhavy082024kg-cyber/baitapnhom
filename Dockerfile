# Backend image. Build:  docker build -t scentstation-be .
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
WORKDIR /app/src
ENV PORT=9999
EXPOSE 9999
CMD ["python", "app.py"]
