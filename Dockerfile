# Vortex Bot — Docker image (Railway / standalone)
FROM python:3.13-slim

WORKDIR /app

# Runtime/build dependencies:
# - build-essential: compile wheels if needed
# - ffmpeg: required for discord.py voice (decode/play audio)
# - fonts-noto-core / fonts-noto-cjk: Unicode rendering (Mongolian/CJK) in rank cards
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    fonts-noto-core \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (layered so dependency cache survives code changes).
# requirements.lock pins the direct deps to the versions this project was
# tested against; requirements.txt is the unpinned range set kept for local
# development. The lock MUST be committed for this build to work.
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

# Application code (src/ package + config.json inside src/, assets for fonts/gifs)
COPY main.py ./main.py
COPY src/ ./src/
COPY assets/ ./assets/
COPY .env.example ./

# Non-root security user
RUN useradd -m -u 1000 vortex && chown -R vortex:vortex /app
USER vortex

# Tokens / Supabase keys must be supplied at runtime via env variables or a
# mounted .env (DISCORD_TOKEN is required at startup).
# The bot connects through the Discord gateway, so no inbound ports are exposed.
CMD ["python", "-m", "src.main"]