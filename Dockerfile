FROM python:3.13-slim

WORKDIR /app

# Runtime/build dependencies:
# - build-essential: compile wheels if needed
# - ffmpeg: required for discord.py voice (decode/play audio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Tokens / Supabase keys must be supplied at runtime via env or mounted .env.
# The bot connects through the Discord gateway, so no inbound ports are exposed.
CMD ["python", "main.py"]
