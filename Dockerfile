FROM python:3.11-slim-bookworm

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


EXPOSE 8080

CMD ["python3", "Flask_api/app.py"]