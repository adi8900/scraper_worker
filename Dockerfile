FROM python:3.12-slim

WORKDIR /app

# Playwright's Node.js needs libatomic; install browsers in a shared path.
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY app ./app

# Celery must not run as root.
RUN useradd --create-home --uid 10001 celeryuser \
    && chmod -R a+rX /ms-playwright /app
USER celeryuser

ENV PYTHONUNBUFFERED=1

CMD ["celery", "-A", "app.workers.celery_app", "worker", "-Q", "scraping,catalog", "--loglevel=info"]
