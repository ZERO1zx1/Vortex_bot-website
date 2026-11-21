FROM python:3.13-slim

WORKDIR /app

COPY aether_bot ./aether_bot

# requirements.txt үндэслэлтэй, doctor нэгэн-хоёртоо дуртай холбоосууд
RUN pip install --no-cache-dir -r aether_bot/requirements.txt

CMD ["python", "aether_bot/bot.py"]
