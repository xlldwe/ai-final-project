FROM python:3.11-slim

WORKDIR /app

COPY bot_telebot/requirements.txt ./bot_telebot/requirements.txt
RUN pip install --no-cache-dir -r bot_telebot/requirements.txt

COPY bot_telebot/ ./bot_telebot/

RUN mkdir -p bot_telebot/data

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "bot_telebot/bot.py"]