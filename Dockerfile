FROM public.ecr.aws/docker/library/python:3.11-slim

ENV POETRY_VERSION=1.8.0 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps:
#   gcc / build-essential / libpq-dev   -> psycopg / asyncpg + manimpango source build
#   ffmpeg                              -> stitching scenes + audio
#   libcairo2 + libcairo2-dev           -> Manim Cairo backend (runtime + headers)
#   libpango-1.0-0 + libpango1.0-dev    -> manimpango needs pangocairo.pc via pkg-config
#                                          (build-from-source; no prebuilt wheel for slim)
#   libpangocairo-1.0-0                 -> Pango Cairo runtime
#   libfreetype6                        -> font rendering
#   libsndfile1                         -> Whisper audio I/O
#   sox                                 -> manim-voiceover post-processes generated speech
#                                          via SoX (audio normalize / clip silence). Missing
#                                          sox -> render fails at voice step in the subprocess.
#   pkg-config                          -> manimpango's setup.py uses pkg-config to discover
#                                          pangocairo headers + version
#   texlive-latex-base + extras + dvisvgm → Manim MathTex / Tex render.
#                                          Without these, any scene with
#                                          mathematical formulas dies with
#                                          "latex failed but did not produce
#                                          a log file." The four packages
#                                          below cover the standard Manim
#                                          tutorial set (AMS math, mathtools,
#                                          xcolor, etc.). Adds ~700 MB to
#                                          the image — worth it; without it
#                                          ~80 % of educational clips fail.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libpq-dev curl ffmpeg \
    libcairo2 libcairo2-dev \
    libpango-1.0-0 libpango1.0-dev libpangocairo-1.0-0 \
    libfreetype6 \
    libsndfile1 \
    sox \
    pkg-config \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-science \
    dvisvgm \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install poetry==$POETRY_VERSION

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --without dev

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
