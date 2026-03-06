FROM python:3.11-slim-bookworm

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').save('/app/models/all-MiniLM-L6-v2')"

EXPOSE 8080

CMD ["python3", "Flask_api/app.py"]