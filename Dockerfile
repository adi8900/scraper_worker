FROM python:3.12-slim

WORKDIR /app

# Playwright's bundled Node.js requires libatomic on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY app ./app

ENV PYTHONUNBUFFERED=1

CMD ["celery", "-A", "app.workers.celery_app", "worker", "-Q", "scraping,catalog", "--loglevel=info"]
