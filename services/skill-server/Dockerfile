FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/skill-server/pyproject.toml /app/pyproject.toml
COPY services/skill-server/app /app/app

RUN pip install --no-cache-dir .

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /run/skill-server /artifacts /state \
    && chown -R appuser:appuser /app /run/skill-server /artifacts /state

USER appuser

CMD ["python", "-m", "app"]
