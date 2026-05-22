# Octoflash Playground Runner — ManimGL (3Blue1Brown's `manimlib`).
#
# This image is the security boundary for the /playground/render endpoint.
# It is invoked by PlaygroundService via `docker run` with --network=none,
# non-root user, capped RAM/CPU/pids, and only the per-render dir mounted RW.
#
# Headless rendering note: ManimGL → moderngl_window → pyglet, and pyglet
# *imports* its window backend (xlib on Linux) and creates a shadow GL
# context at import time. There's no display in a container, so we run the
# whole manimgl invocation under xvfb-run (a virtual X server). MESA does
# the actual OpenGL via software, so no GPU is required — short scenes only.

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # MESA software OpenGL — works without GPU.
    LIBGL_ALWAYS_SOFTWARE=1 \
    MESA_GL_VERSION_OVERRIDE=3.3

# Runtime + build deps. ManimGL pulls native wheels for moderngl, pycairo,
# manimpango — they need cairo/pango/freetype/ffmpeg at runtime and
# pkg-config + headers at build time.
#
# TeX Live is needed because ManimGL's `Tex(...)` / `MathTex(...)` shell out
# to `latex` + `dvisvgm`. The "recommended" + "extra" packages cover the
# vast majority of math typesetting — `latexmk` and the cm-super fonts add
# ~700 MB but the alternative (no math text in the playground) is worse.
# xvfb / xauth are kept as a fallback path even though the default mode is
# EGL-headless — useful when debugging GL stack issues.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        xvfb \
        xauth \
        x11-utils \
        libcairo2 \
        libcairo2-dev \
        libpango-1.0-0 \
        libpango1.0-dev \
        libpangocairo-1.0-0 \
        libfreetype6 \
        libgl1 \
        libglu1-mesa \
        libegl1 \
        libgles2 \
        libgbm1 \
        libosmesa6 \
        libxext6 \
        libxrender1 \
        libxi6 \
        libsdl2-2.0-0 \
        pkg-config \
        build-essential \
        git \
        texlive-latex-base \
        texlive-latex-extra \
        texlive-latex-recommended \
        texlive-fonts-recommended \
        texlive-fonts-extra \
        texlive-science \
        tipa \
        cm-super \
        dvisvgm \
    && rm -rf /var/lib/apt/lists/*

# ManimGL is the 3Blue1Brown distribution. PyPI package: `manimgl`. Python
# import: `manimlib`. CLI: `manimgl`.
RUN pip install --no-cache-dir manimgl

# Force moderngl's standalone context to use the EGL backend (which works
# headless via MESA software) instead of the X11 default that needs a
# DISPLAY. ManimGL's Camera.init_context calls `moderngl.create_standalone_context()`
# with no args — we patch it at Python startup so every render gets EGL.
RUN printf '%s\n' \
  'import moderngl' \
  '_orig = moderngl.create_standalone_context' \
  'def _egl_default(*args, **kwargs):' \
  '    kwargs.setdefault("backend", "egl")' \
  '    return _orig(*args, **kwargs)' \
  'moderngl.create_standalone_context = _egl_default' \
  > /usr/local/lib/python3.11/site-packages/sitecustomize.py

# Wrapper: tell pyglet to use its headless EGL backend, then exec manimgl.
#
# PYGLET_HEADLESS=1 makes pyglet skip xlib entirely and create an EGL
# offscreen surface backed by MESA. This avoids both the X server and the
# xauth-cookie hang in `xvfb-run`. libegl1 / libgles2 / libosmesa6 (above)
# are what MESA uses.
RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  'export PYGLET_HEADLESS=1' \
  'export LIBGL_ALWAYS_SOFTWARE=1' \
  'export MESA_GL_VERSION_OVERRIDE=3.3' \
  'exec manimgl "$@"' \
  > /usr/local/bin/run-manimgl \
 && chmod +x /usr/local/bin/run-manimgl

# Non-root user — matches the uid PlaygroundService passes via --user.
RUN useradd -ms /bin/bash -u 1000 runner
USER 1000:1000
WORKDIR /work

# No ENTRYPOINT in the image — PlaygroundService sets it to
# /usr/local/bin/run-manimgl at `docker run` time.
