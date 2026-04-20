FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/live_data/src

WORKDIR /app/live_data

COPY live_data/requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

COPY live_data/README.md ./README.md
COPY live_data/pyproject.toml ./pyproject.toml
COPY live_data/sql ./sql
COPY live_data/src ./src

ENTRYPOINT ["python", "-m", "rtd_collector.main"]
CMD ["--log-level", "INFO"]
