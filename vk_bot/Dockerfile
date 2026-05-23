FROM python:3.11-slim

WORKDIR /app

COPY vk_bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY vk_bot/ ./vk_bot/

CMD ["python", "-m", "vk_bot.main"]
