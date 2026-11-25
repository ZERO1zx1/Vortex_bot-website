FROM python:3.13-slim

WORKDIR /app

COPY aether_bot ./aether_bot

# Runtime dependencies only; DATABASE_URL and DISCORD_TOKEN come from env.
RUN pip install --no-cache-dir -r aether_bot/requirements.txt

CMD ["python", "aether_bot/bot.py"]
