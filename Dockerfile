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

# Pre-warm LaTeX font/format cache at image-build time. Without this,
# the FIRST render on a fresh container spends 5–10 min building the
# cache — and with N parallel Manim subprocesses each racing for the
# same cache files, all of them starve and hit the activity timeout.
# Running once at build-time bakes the cache into the image layer so
# every subsequent container starts hot.
#
# `|| true` because LaTeX warmup is best-effort — Docker build must
# not fail if a font/package isn't quite where we expect. The
# `texlive-*` install above is what actually matters; this just
# pre-populates the cache.
RUN echo '\documentclass{article}\begin{document}$x^2$\end{document}' > /tmp/warmup.tex \
 && cd /tmp && latex -interaction=nonstopmode warmup.tex >/dev/null 2>&1 || true \
 && rm -f warmup.*

# Node.js 20 — required by the bgutil PO Token provider's
# `generate_once.js` script. YouTube rolled out a PO Token (proof-of-
# origin) requirement in 2025 that gates every non-storyboard format;
# even with valid cookies, yt-dlp gets audio-only / storyboards
# without it. The bgutil plugin (`bgutil-ytdlp-pot-provider` pip
# package, already in pyproject) mints tokens via a Node script —
# this layer installs the runtime + clones+builds the script source.
ARG BGUTIL_VERSION=1.3.1
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL "https://github.com/Brainicism/bgutil-ytdlp-pot-provider/archive/refs/tags/${BGUTIL_VERSION}.tar.gz" \
    | tar -xz -C /opt \
 && mv "/opt/bgutil-ytdlp-pot-provider-${BGUTIL_VERSION}" /opt/bgutil-pot-provider \
 && cd /opt/bgutil-pot-provider/server \
 && npm install --omit=dev \
 && npm run build
ENV BGUTIL_POT_PROVIDER_SERVER_HOME=/opt/bgutil-pot-provider/server

RUN pip install --upgrade pip \
    && pip install poetry==$POETRY_VERSION

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --without dev

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
