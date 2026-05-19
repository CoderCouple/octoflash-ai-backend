FROM public.ecr.aws/docker/library/python:3.11-slim

ENV POETRY_VERSION=1.8.0 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps:
#   gcc / libpq-dev  -> psycopg/asyncpg
#   ffmpeg           -> stitching scenes + audio
#   libcairo2 / libpango / pkg-config -> Manim native deps
#   libsndfile1 / libsox-fmt-all      -> Whisper audio I/O
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl ffmpeg \
    libcairo2 libcairo2-dev libpango-1.0-0 libpangocairo-1.0-0 pkg-config \
    libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install poetry==$POETRY_VERSION

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --without dev

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
