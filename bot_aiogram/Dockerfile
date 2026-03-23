FROM python:3.11-slim

WORKDIR /app

COPY bot_aiogram/requirements.txt ./bot_aiogram/requirements.txt
RUN pip install --no-cache-dir -r bot_aiogram/requirements.txt

COPY bot_aiogram/ ./bot_aiogram/

RUN mkdir -p bot_aiogram/data

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "bot_aiogram/bot.py"]